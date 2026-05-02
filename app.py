from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
import pandas as pd
import numpy as np
import os
import random
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
import qrcode
import base64
from io import BytesIO

from extensions import db
from models import User, Product, Transaction, ActivityLog, Dataset, ChatSession, ChatMessage
from nlp_engine import generate_response, analyze_dataset
from ml_engine import train_sales_forecast
from security_utils import encrypt_file, decrypt_file_to_df

# ───────────────────────────────
# APP CONFIG
# ───────────────────────────────

app = Flask(__name__, template_folder="templates", static_folder="static")

# Secret key (safe for deployment)
app.secret_key = os.environ.get("SECRET_KEY", "fluxlogic-secret-key")

# Database (Absolute path for reliability)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "fluxlogic.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email Config (use env in real deploy)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME", "")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD", "")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("MAIL_USERNAME", "noreply@fluxlogic.ai")

mail = Mail(app)

# Init DB
db.init_app(app)

# Login Manager
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create DB
with app.app_context():
    db.create_all()

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Context processor
@app.context_processor
def inject_now():
    return {"now": datetime.now()}

# Logging helper
def add_log(action):
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        db.session.add(ActivityLog(user_id=user_id, action=action))
        db.session.commit()
    except Exception as e:
        print(e)
        db.session.rollback()

# ───────────────────────────────
# AUTH ROUTES
# ───────────────────────────────

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("datasets"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("login.html")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.is_2fa_enabled:
                session["temp_user_id"] = user.id
                return redirect(url_for("verify_2fa"))
            
            login_user(user, remember=True)
            add_log("User logged in")
            return redirect(url_for("datasets"))

        flash("Invalid username or password. Please check your credentials.", "error")

    return render_template("index.html")

@app.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    user_id = session.get("temp_user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    user = db.session.get(User, user_id)
    if not user.two_factor_secret:
        flash("2FA not setup.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        pin = request.form.get("pin")
        totp = pyotp.TOTP(user.two_factor_secret)
        if totp.verify(pin):
            login_user(user, remember=True)
            session.pop("temp_user_id")
            add_log("User logged in (2FA)")
            return redirect(url_for("datasets"))
        else:
            flash("Invalid verification code.", "error")
            
    return render_template("verify_2fa.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("datasets"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields (username, email, password) are required.", "error")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("That username is already taken. Try another.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash("Success! Your account is ready. Please sign in.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    add_log("User logged out")
    logout_user()
    return redirect(url_for("login"))

# ───────────────────────────────
# SETTINGS & 2FA
# ───────────────────────────────

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        current_user.username = request.form.get("username", current_user.username)
        current_user.email = request.form.get("email", current_user.email)
        current_user.store_name = request.form.get("store_name", current_user.store_name)
        current_user.theme_preference = request.form.get("theme", current_user.theme_preference)
        current_user.font_size = int(request.form.get("font_size", current_user.font_size))
        
        db.session.commit()
        flash("Profile and preferences updated.", "success")
        return redirect(url_for("settings"))

    return render_template("settings.html")

@app.route("/setup-2fa", methods=["GET", "POST"])
@login_required
def setup_2fa():
    if request.method == "POST":
        pin = request.form.get("pin")
        totp = pyotp.TOTP(current_user.two_factor_secret)
        if totp.verify(pin):
            current_user.is_2fa_enabled = True
            db.session.commit()
            flash("2FA has been successfully enabled for your account.", "success")
            return redirect(url_for("settings"))
        else:
            flash("Invalid code. Please try scanning the QR code again.", "error")

    if not current_user.two_factor_secret:
        current_user.two_factor_secret = pyotp.random_base32()
        db.session.commit()
    
    totp = pyotp.TOTP(current_user.two_factor_secret)
    provisioning_uri = totp.provisioning_uri(name=current_user.email, issuer_name="FluxLogic")
    
    img = qrcode.make(provisioning_uri)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return render_template("setup_2fa.html", qr_code=qr_base64, secret=current_user.two_factor_secret)

@app.route("/disable-2fa")
@login_required
def disable_2fa():
    current_user.two_factor_secret = None
    current_user.is_2fa_enabled = False
    db.session.commit()
    flash("Two-Factor Authentication has been removed.", "info")
    return redirect(url_for("settings"))

# ───────────────────────────────
# DATASET MANAGEMENT
# ───────────────────────────────

@app.route("/datasets")
@login_required
def datasets():
    user_datasets = Dataset.query.filter_by(user_id=current_user.id).all()
    return render_template("datasets.html", datasets=user_datasets)

@app.route("/upload", methods=["POST"])
@login_required
def upload_dataset():
    if "dataset" not in request.files:
        flash("Please select a file to upload.", "error")
        return redirect(url_for("datasets"))

    file = request.files["dataset"]

    if file and file.filename.endswith(".csv"):
        filename = f"{current_user.id}_{datetime.now().timestamp()}_{file.filename}"
        file_path = DATA_DIR / filename
        try:
            file.save(file_path)
            
            new_dataset = Dataset(
                user_id=current_user.id,
                original_name=file.filename,
                filename=filename
            )
            db.session.add(new_dataset)
            db.session.commit()
            
            encrypt_file(file_path, app.secret_key)
            flash(f"'{file.filename}' is now secured and ready for analysis.", "success")
        except Exception as e:
            print(e)
            db.session.rollback()
            flash("File processing failed", "error")
    else:
        flash("We currently only support CSV files. Please check your file format.", "error")

    return redirect(url_for("datasets"))

@app.route("/dataset/<int:dataset_id>/options")
@login_required
def dataset_options(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return redirect(url_for("datasets"))
    return render_template("options.html", dataset=dataset)

@app.route("/dataset/<int:dataset_id>/delete")
@login_required
def delete_dataset(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id == current_user.id:
        file_path = DATA_DIR / dataset.filename
        if file_path.exists():
            file_path.unlink()
        db.session.delete(dataset)
        db.session.commit()
        flash(f"Removed dataset '{dataset.original_name}' from your library.", "info")
    return redirect(url_for("datasets"))

# ───────────────────────────────
# ANALYSIS & CHAT
# ───────────────────────────────

@app.route("/dataset/<int:dataset_id>/dashboard")
@login_required
def dataset_dashboard(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return redirect(url_for("datasets"))
    
    file_path = DATA_DIR / dataset.filename
    try:
        df = decrypt_file_to_df(file_path, app.secret_key)
    except Exception as e:
        print(e)
        flash("Unable to securely access this dataset.", "error")
        return redirect(url_for("datasets"))
    
    from nlp_engine import detect_currency
    currency = detect_currency(df)

    # 1) Find Date Column first
    date_col = None
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            date_col = c
            break
        try:
            sample = df[c].dropna().head(10).astype(str)
            if sample.str.match(r'^\d{4}-\d{2}-\d{2}').mean() > 0.3:
                df[c] = pd.to_datetime(df[c], errors='coerce')
                date_col = c
                break
        except: pass

    charts = []
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    # 2) Generate charts for up to 3 numeric columns
    for col in numeric_cols[:3]:
        if date_col:
            time_data = df.groupby(df[date_col].dt.date)[col].sum().tail(15)
            charts.append({
                "type": "line",
                "title": f"{col.capitalize()} Trend",
                "labels": [str(x) for x in time_data.index],
                "data": [float(x) if pd.notnull(x) else 0 for x in time_data.values],
                "description": f"Tracking the sum of {col} over the most recent time periods."
            })
        else:
            charts.append({
                "type": "bar",
                "title": f"{col.capitalize()} Overview",
                "labels": [str(x) for x in df.head(15).index],
                "data": [float(x) if pd.notnull(x) else 0 for x in df[col].head(15).tolist()],
                "description": f"Visualizing {col} across the first 15 records in the dataset."
            })

    # 3) Generate charts for up to 3 categorical columns
    for col in categorical_cols[:3]:
        counts = df[col].value_counts().head(6)
        charts.append({
            "type": "pie" if len(counts) <= 4 else "doughnut",
            "title": f"Distribution: {col.capitalize()}",
            "labels": [str(x) for x in counts.index],
            "data": [float(x) for x in counts.values],
            "description": f"Visual breakdown of the most frequent segments within the {col} category."
        })

    return render_template("dynamic_dashboard.html", dataset=dataset, charts=charts, currency=currency)

@app.route("/dataset/<int:dataset_id>/chat", methods=["GET", "POST"])
@login_required
def dataset_chat(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return redirect(url_for("datasets"))
    
    session_id = request.args.get("session_id")
    
    if request.args.get("new") == "1":
        # Create a new session
        chat_sess = ChatSession(user_id=current_user.id, dataset_id=dataset.id)
        db.session.add(chat_sess)
        db.session.commit()
        return redirect(url_for("dataset_chat", dataset_id=dataset.id, session_id=chat_sess.id))
    elif not session_id:
        # Auto-load the most recent session if it exists
        latest_sess = ChatSession.query.filter_by(user_id=current_user.id, dataset_id=dataset.id).order_by(ChatSession.created_at.desc()).first()
        if latest_sess:
            return redirect(url_for("dataset_chat", dataset_id=dataset.id, session_id=latest_sess.id))
        else:
            # Create the first session
            chat_sess = ChatSession(user_id=current_user.id, dataset_id=dataset.id)
            db.session.add(chat_sess)
            db.session.commit()
            return redirect(url_for("dataset_chat", dataset_id=dataset.id, session_id=chat_sess.id))
    
    chat_sess = ChatSession.query.get_or_404(session_id)
    if request.method == "POST":
        data = request.get_json()
        user_msg = data.get("message") if data else None
        
        if user_msg:
            db.session.add(ChatMessage(session_id=chat_sess.id, role="user", content=user_msg))
            file_path = DATA_DIR / dataset.filename
            ai_content = generate_response(user_msg, file_path, app.secret_key)
            db.session.add(ChatMessage(session_id=chat_sess.id, role="ai", content=ai_content))
            db.session.commit()
            
            return jsonify({
                "status": "ok",
                "reply": ai_content,
                "time": datetime.now().strftime('%H:%M')
            })
        return jsonify({"status": "error", "message": "No message provided"}), 400

    sessions = ChatSession.query.filter_by(user_id=current_user.id, dataset_id=dataset.id).order_by(ChatSession.created_at.desc()).all()
    messages = ChatMessage.query.filter_by(session_id=chat_sess.id).order_by(ChatMessage.timestamp.asc()).all()
    
    return render_template("chat_ui.html", dataset=dataset, active_session=chat_sess, messages=messages, all_sessions=sessions)

@app.route("/dataset/<int:dataset_id>/predictions")
@login_required
def dataset_predictions(dataset_id):
    dataset = Dataset.query.get_or_404(dataset_id)
    if dataset.user_id != current_user.id:
        return redirect(url_for("datasets"))
    
    try:
        df = decrypt_file_to_df(file_path, app.secret_key)
    except:
        flash("Unable to access dataset for predictions.", "error")
        return redirect(url_for("datasets"))
        
    analysis = analyze_dataset(file_path, app.secret_key)
    forecast = train_sales_forecast(df)
    
    # Get currency for the template
    from nlp_engine import detect_currency
    currency = detect_currency(df)
    
    return render_template("predictions.html", dataset=dataset, analysis=analysis, forecast=forecast, currency=currency)

# ───────────────────────────────
# ERROR HANDLING
# ───────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("login.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("index.html", error=str(e)), 500

# ───────────────────────────────
# RUN
# ───────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)