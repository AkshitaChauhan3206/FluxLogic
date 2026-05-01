import re
import pandas as pd
import numpy as np
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from security_utils import decrypt_file_to_df

# ─────────────────────────────────────────────
# ADVANCED TRAINING DATA (Intent Mapping)
# ─────────────────────────────────────────────
TRAINING_DATA = [
    ("hello", "greeting"), ("hi", "greeting"), ("hii", "greeting"), ("hey", "greeting"), ("how are you", "greeting"), ("good morning", "greeting"),
    ("how many rows", "size"), ("how many records", "size"), ("dataset size", "size"), ("count", "size"), ("volume", "size"), ("entries", "size"),
    ("what is the total profit", "profit"), ("total revenue", "profit"), ("earnings", "profit"), ("sales", "profit"), ("money", "profit"), ("value", "profit"), ("sum", "profit"),
    ("what is the average", "average"), ("mean value", "average"), ("typical value", "average"), ("average amount", "average"), ("mean", "average"), ("standard", "average"),
    ("best category", "top_items"), ("top performers", "top_items"), ("who is the best", "top_items"), ("top 3", "top_items"), ("leaders", "top_items"), ("peak performers", "top_items"),
    ("worst", "worst_items"), ("lowest", "worst_items"), ("underperforming", "worst_items"), ("bad performers", "worst_items"), ("bottom", "worst_items"), ("struggling", "worst_items"),
    ("trend", "trend"), ("growth", "trend"), ("changes over time", "trend"), ("monthly stats", "trend"), ("timeline", "trend"), ("history", "trend"), ("momentum", "trend"),
    ("distribution", "distribution"), ("breakdown", "distribution"), ("categories", "distribution"), ("segments", "distribution"), ("groups", "distribution"), ("clusters", "distribution"),
    ("advice", "advice"), ("strategy", "advice"), ("what should i do", "advice"), ("recommendation", "advice"), ("tips", "advice"), ("help me grow", "advice"), ("suggestions", "advice"),
    ("summary", "summary"), ("report", "summary"), ("tell me about my data", "summary"), ("what does the data say", "summary"), ("overview", "summary"), ("brief", "summary"),
    ("outliers", "outliers"), ("anomalies", "outliers"), ("extreme values", "outliers"), ("weird data", "outliers"), ("wrong data", "outliers"), ("spikes", "outliers"),
    ("compare", "comparison"), ("difference", "comparison"), ("better or worse", "comparison"), ("contrast", "comparison"), ("vs", "comparison"), ("relative", "comparison"),
    ("what can you do", "help"), ("help", "help"), ("commands", "help"), ("how to use", "help"), ("options", "help"), ("features", "help")
]

X_train, y_train = zip(*TRAINING_DATA)
model = make_pipeline(TfidfVectorizer(ngram_range=(1, 3)), MultinomialNB(alpha=0.01))
model.fit(X_train, y_train)

# ─────────────────────────────────────────────
# DYNAMIC PHRASE REPOSITORY (ChatGPT Style)
# ─────────────────────────────────────────────
INTROS = [
    "Certainly! I've carefully analyzed your dataset and discovered some very interesting insights for you: ",
    "Great question! Looking into the records, I can clearly see that ",
    "I've performed a deep dive into your data patterns. 😊 Here is the breakdown: ",
    "According to the latest strategic analysis of your business figures, ",
    "I'd be happy to explain that! Based on the patterns in your dataset: ",
    "Interesting point! I've cross-referenced the columns and found that: ",
    "Let me check that for you... Ah, I see! Here's the situation: ",
    "That's a vital question for any business leader. My analysis shows: ",
    "I've summarized the key drivers in your data for you: "
]

OUTROS = [
    "\n\nDoes this align with your current business goals? 😊",
    "\n\nI can dive deeper into these specific categories if you'd like! 🚀",
    "\n\nWould you like me to look for any hidden patterns in other segments? ✨",
    "\n\nI'm ready for your next question! What else can I analyze for you? 😊",
    "\n\nHopefully, this insight provides a clear path for your next steps! 🌟",
    "\n\nThis is just the surface—the Dashboard has even more visual details! 📊",
    "\n\nLet me know if you want me to compare this to any other metric! 😊"
]

def profile_dataset(df):
    numeric_cols = [c for c in df.select_dtypes(include=['number']).columns if 'id' not in c.lower()]
    val_col = next((c for c in numeric_cols if any(x in c.lower() for x in ['profit', 'sale', 'revenue', 'amount', 'total', 'price', 'income'])), numeric_cols[0] if numeric_cols else None)
    cat_col = next((c for c in df.select_dtypes(include=['object', 'category']).columns if 1 < df[c].nunique() <= 50), None)
    
    date_col = None
    for c in df.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(df[c]): date_col = c; break
            if df[c].dtype == object and df[c].astype(str).str.match(r'^\d{4}-\d{2}-\d{2}').mean() > 0.3:
                df[c] = pd.to_datetime(df[c], errors='coerce')
                date_col = c; break
        except: pass
    return val_col, cat_col, date_col, numeric_cols

def fmt(val):
    try:
        if abs(val) >= 1_000_000: return f"${val/1_000_000:,.2f}M"
        if abs(val) >= 1_000: return f"${val:,.2f}"
        return f"${val:.2f}"
    except: return str(val)

def generate_response(query, dataset_path, secret_key):
    try:
        df = decrypt_file_to_df(dataset_path, secret_key)
    except: return "❌ I'm sorry, I couldn't decrypt the dataset for analysis. Please check your encryption keys! 😊"
    
    val_col, cat_col, date_col, numeric_cols = profile_dataset(df)
    
    # Keyword Mapping (Fallback)
    kw_map = {
        "profit": "profit", "revenue": "profit", "sales": "profit", "money": "profit", "value": "profit", "earnings": "profit",
        "average": "average", "mean": "average", "typical": "average", "standard": "average",
        "best": "top_items", "top": "top_items", "highest": "top_items", "leader": "top_items", "peak": "top_items",
        "worst": "worst_items", "lowest": "worst_items", "bottom": "worst_items", "struggling": "worst_items",
        "trend": "trend", "growth": "trend", "history": "trend", "timeline": "trend", "momentum": "trend",
        "summary": "summary", "report": "summary", "overview": "summary", "brief": "summary",
        "help": "help", "how": "help", "can you": "help", "commands": "help", "options": "help",
        "how many": "size", "rows": "size", "records": "size", "volume": "size", "entries": "size",
        "distribution": "distribution", "breakdown": "distribution", "categories": "distribution", "segments": "distribution",
        "compare": "comparison", "difference": "comparison", "vs": "comparison",
        "outliers": "outliers", "anomalies": "outliers", "weird": "outliers", "spikes": "outliers"
    }
    
    # ── DYNAMIC ENTITY DETECTION & FILTERING ──
    filter_applied = None
    if cat_col:
        unique_vals = df[cat_col].unique()
        for val in unique_vals:
            if str(val).lower() in query.lower():
                df = df[df[cat_col] == val]
                filter_applied = f"**{val}**"
                break
    
    # Check for Month/Year in query
    if date_col:
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        for i, m in enumerate(months):
            if m in query.lower():
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df = df[df[date_col].dt.month == (i + 1)]
                filter_applied = f"{filter_applied + ' in ' if filter_applied else ''}**{m.capitalize()}**"
                break

    if df.empty:
        return f"🕵️ I found no records matching your query for {filter_applied}. Try asking about a different category or time period! 😊"

    forced_intent = next((intent for kw, intent in kw_map.items() if kw in query.lower()), None)
    probs = model.predict_proba([query.lower()])[0]
    best_intent = forced_intent if forced_intent else model.classes_[np.argmax(probs)]
    confidence = np.max(probs)

    if not forced_intent and confidence < 0.08:
        # Check if they just mentioned a column
        found_col = next((c for c in df.columns if c.lower() in query.lower()), None)
        if found_col:
            if found_col in numeric_cols:
                return f"📊 For **{found_col}**, the total is {fmt(df[found_col].sum())} with an average of {fmt(df[found_col].mean())}. {outro}"
            else:
                top_v = df[found_col].mode()[0] if not df[found_col].empty else "N/A"
                return f"🔍 Looking at **{found_col}**, the most common value is **{top_v}**. {outro}"
        return "🤔 I'm not entirely sure I understood that perfectly! Could you ask me specifically about your **total profit**, **top categories**, **average values**, **trends**, or **size**? I'm eager to help! 😊"

    intro = random.choice(INTROS)
    if filter_applied:
        intro = f"Filtering for {filter_applied}, " + intro.lower()
    
    outro = random.choice(OUTROS)

    # ── GREETING ──
    if best_intent == "greeting":
        return f"👋 {random.choice(['Hello!', 'Hi there!', 'Greetings!'])} I'm your friendly FluxLogic AI Guide. I've analyzed your data and I'm so happy to help you grow your business today! You can ask me about **profit**, **top segments**, **trends**, or even **detect outliers**. What's on your mind? 😊"

    # ── HELP ──
    if best_intent == "help":
        return "🛠️ **I am here to make your data work for you!**\n\nYou can ask me things like:\n• **Performance**: 'What is my total profit?' 💰\n• **Rankings**: 'Who are my top 3 categories?' 🏆\n• **Trends**: 'Show me the growth over time.' 📈\n• **Averages**: 'What is the average sale value?' 📊\n• **Outliers**: 'Find any weird data points.' 🔍\n• **Segments**: 'Give me a breakdown of categories.' 🥧\n\nI can also **compare** different segments for you! Just ask naturally. 😊"

    # ── SIZE ──
    if best_intent == "size":
        return f"{intro} Your dataset currently manages a volume of **{len(df):,}** individual records. This provides a robust statistical foundation for our analysis! {outro}"

    # ── SUMMARY ──
    if best_intent == "summary":
        res = [f"{intro}I've prepared a strategic overview:"]
        res.append(f"• **Volume**: We are analyzing **{len(df):,}** total business entries.")
        if val_col: res.append(f"• **Value**: Your total accumulated **{val_col}** stands at **{fmt(df[val_col].sum())}**. That's quite impressive! ✨")
        if cat_col: res.append(f"• **Leadership**: Your most active segment is currently **{df[cat_col].value_counts().index[0]}**, representing a key pillar of your operations. 🌟")
        return "\n".join(res) + outro

    # ── PROFIT ──
    if best_intent == "profit" and val_col:
        total = df[val_col].sum()
        avg = df[val_col].mean()
        return f"{intro} The total **{val_col}** calculated from your data is **{fmt(total)}**. On average, each record contributes about {fmt(avg)} to your business goals. {outro}"

    # ── TOP ITEMS ──
    if best_intent == "top_items" and cat_col and val_col:
        top = df.groupby(cat_col)[val_col].sum().sort_values(ascending=False).head(3)
        res = [f"{intro} Here are your **Top 3 {cat_col}** based on performance:"]
        for k, v in top.items():
            res.append(f"• **{k}**: Contributing **{fmt(v)}** in total value. 🏆")
        return "\n".join(res) + outro

    # ── WORST ITEMS ──
    if best_intent == "worst_items" and cat_col and val_col:
        worst = df.groupby(cat_col)[val_col].sum().sort_values(ascending=True).head(3)
        res = [f"{intro} I've identified the **Bottom 3 {cat_col}** which may need attention:"]
        for k, v in worst.items():
            res.append(f"• **{k}**: Total value of **{fmt(v)}**. 📉")
        return "\n".join(res) + outro

    # ── AVERAGE ──
    if best_intent == "average" and val_col:
        avg_val = df[val_col].mean()
        return f"{intro} The average **{val_col}** across your dataset is **{fmt(avg_val)}**. This is your baseline performance metric. {outro}"

    # ── DISTRIBUTION ──
    if best_intent == "distribution" and cat_col:
        dist = df[cat_col].value_counts().head(5)
        res = [f"{intro} Here is the breakdown of your top 5 **{cat_col}** segments:"]
        for k, v in dist.items():
            res.append(f"• **{k}**: {v} records ({v/len(df)*100:.1f}%)")
        return "\n".join(res) + outro

    # ── COMPARISON ──
    if best_intent == "comparison" and cat_col and val_col:
        comp = df.groupby(cat_col)[val_col].sum().sort_values(ascending=False).head(5)
        res = [f"{intro} Comparing the top **{cat_col}** by **{val_col}**:"]
        for k, v in comp.items():
            res.append(f"• **{k}**: {fmt(v)}")
        return "\n".join(res) + outro

    # ── OUTLIERS ──
    if best_intent == "outliers" and val_col:
        q1 = df[val_col].quantile(0.25)
        q3 = df[val_col].quantile(0.75)
        iqr = q3 - q1
        outliers = df[(df[val_col] < (q1 - 1.5 * iqr)) | (df[val_col] > (q3 + 1.5 * iqr))]
        if not outliers.empty:
            return f"{intro} I found **{len(outliers)} outliers** in your **{val_col}** column. These are data points that significantly deviate from the norm (e.g., unusually high or low values). You might want to review them for anomalies! 🔍 {outro}"
        return f"{intro} Great news! No significant outliers were detected in your **{val_col}**. Your data seems very consistent. 😊 {outro}"

    # ── TREND ──
    if best_intent == "trend" and date_col and val_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        recent = df.groupby(df[date_col].dt.date)[val_col].sum().tail(5)
        res = [f"{intro} Looking at your most recent timeline:"]
        for k, v in recent.items():
            res.append(f"• On {k}: You recorded **{fmt(v)}**. 📈")
        res.append("\nThe momentum looks interesting! We should keep an eye on these shifts.")
        return "\n".join(res) + outro

    # ── ADVICE ──
    if best_intent == "advice":
        if val_col and cat_col:
            best = df.groupby(cat_col)[val_col].sum().idxmax()
            return f"{intro} Based on the numbers, my top strategic tip is to **double down on {best}**. It is currently your most productive segment and has the highest ROI potential! 🚀 {outro}"
        return f"{intro} I recommend focusing on your top 20% high-value records (Pareto Principle). This is usually where 80% of your growth originates! 😊 {outro}"

    return f"✨ I've analyzed your request! While I can see several patterns, for the best visual clarity, I highly recommend checking out the **Intelligence Dashboard**. It will give you a full 360-degree view of what I'm seeing! 😊"

def analyze_dataset(dataset_path, secret_key):
    """Deep AI Analysis with Pattern Recognition"""
    try:
        df = decrypt_file_to_df(dataset_path, secret_key)
    except: return {"error": "Dataset decryption failed"}

    val_col, cat_col, date_col, numeric_cols = profile_dataset(df)
    num_rows, num_cols = df.shape

    summary = f"I have analyzed {num_rows} records. Total {val_col} is {fmt(df[val_col].sum())}." if val_col else f"Analyzed {num_rows} records."

    patterns = []
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr()
        for i in range(len(numeric_cols)):
            for j in range(i+1, len(numeric_cols)):
                val = corr.iloc[i, j]
                if abs(val) > 0.4:
                    patterns.append(f"Correlation ({val:.2f}) between {numeric_cols[i]} and {numeric_cols[j]}.")

    pareto_insight = f"Top segments drive majority of {val_col}." if val_col else ""

    numeric_stats = []
    for c in numeric_cols[:6]:
        col_data = df[c].dropna()
        numeric_stats.append({
            "column": c.capitalize(),
            "total": fmt(col_data.sum()), "average": fmt(col_data.mean()),
            "min": fmt(col_data.min()), "max": fmt(col_data.max()), "std": fmt(col_data.std())
        })

    return {
        "summary": summary, "numeric_stats": numeric_stats, "patterns": patterns, "pareto": pareto_insight,
        "top_performers": [{"name": str(k), "value": fmt(v)} for k, v in df.groupby(cat_col)[val_col].sum().sort_values(ascending=False).head(5).items()] if cat_col and val_col else [],
        "weak_performers": [{"name": str(k), "value": fmt(v)} for k, v in df.groupby(cat_col)[val_col].sum().sort_values(ascending=True).head(3).items()] if cat_col and val_col else [],
        "val_col": val_col.capitalize() if val_col else "Value",
        "recommendation": "Optimize top segments and monitor correlations."
    }
