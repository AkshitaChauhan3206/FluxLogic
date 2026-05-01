from pathlib import Path
import pandas as pd
from sklearn.linear_model import LinearRegression

DATA_DIR = Path("data")
MODEL_FILE = DATA_DIR / "sales_model.csv"

def load_dataset():
    path = DATA_DIR / "ML-Dataset.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df

def train_sales_forecast():
    df = load_dataset()
    if df.empty:
        return {"status": "error", "message": "ML-Dataset.csv not found or empty.", "predictions": []}

    date_col = None
    sales_col = None

    for c in df.columns:
        if c in ["date", "order_date", "timestamp", "transaction_date"]:
            date_col = c
        if c in ["sales", "sale", "amount", "revenue", "profit"]:
            sales_col = c

    if date_col is None or sales_col is None:
        return {"status": "error", "message": "Dataset must have date and sales/amount columns.", "predictions": []}

    df = df[[date_col, sales_col]].dropna().copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna()
    if len(df) < 2:
        return {"status": "error", "message": "Not enough data to train.", "predictions": []}

    df = df.sort_values(date_col)
    df["day_index"] = range(len(df))

    X = df[["day_index"]]
    y = df[sales_col].astype(float)

    model = LinearRegression()
    model.fit(X, y)

    future = []
    last_index = int(df["day_index"].iloc[-1])
    last_date = df[date_col].iloc[-1]

    for i in range(1, 8):
        idx = last_index + i
        pred = float(model.predict([[idx]])[0])
        future.append({
            "date": (last_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
            "value": round(max(pred, 0), 2),
            "purpose": "Plan inventory and cash flow for the next day.",
            "description": "Forecasted using linear regression from your dataset history."
        })

    return {"status": "ok", "message": "Forecast created successfully.", "predictions": future}

def diagnostics():
    df = load_dataset()
    if df.empty:
        return "No dataset found for diagnostics."

    cols = [c.lower() for c in df.columns]
    if "sales" in cols and "expenses" in cols:
        revenue = float(df["sales"].sum())
        expenses = float(df["expenses"].sum())
    elif "amount" in cols and "type" in cols:
        sales = df[df["type"].astype(str).str.lower() == "sale"]["amount"].sum()
        expenses = df[df["type"].astype(str).str.lower() == "expense"]["amount"].sum()
        revenue = float(sales)
        expenses = float(expenses)
    else:
        return "Diagnostics unavailable because dataset columns do not match expected format."

    if revenue > 0 and expenses > 0.4 * revenue:
        return "Diagnostic: High overhead detected. Suggestion: Review Utility or Rent costs."
    return "Diagnostic: Expense level is within acceptable range."