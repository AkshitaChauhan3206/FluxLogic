import os
from pathlib import Path
import pandas as pd
from sklearn.linear_model import LinearRegression

# Use absolute path for reliability
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def load_dataset(filename="ML-Dataset.csv"):
    path = DATA_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def train_sales_forecast(df=None):
    """Trains a forecast model. If df is provided, uses it; otherwise loads default."""
    if df is None:
        df = load_dataset()
    
    if df.empty:
        return {"status": "error", "message": "No data available for forecasting.", "predictions": []}

    # Standardize columns for the engine
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    date_col = None
    sales_col = None

    # Priority mapping for columns
    date_candidates = ["date", "order_date", "timestamp", "transaction_date", "time"]
    sales_candidates = ["sales", "sale", "amount", "revenue", "profit", "total"]

    for c in df.columns:
        if any(cand in c for cand in date_candidates):
            date_col = c
            break
    
    for c in df.columns:
        if any(cand in c for cand in sales_candidates):
            sales_col = c
            break

    if not date_col or not sales_col:
        # Fallback: find first datetime-like and first numeric
        for c in df.columns:
            if not date_col:
                try:
                    pd.to_datetime(df[c].head(5), errors='raise')
                    date_col = c
                except: pass
            if not sales_col and pd.api.types.is_numeric_dtype(df[c]):
                sales_col = c
                
    if date_col is None or sales_col is None:
        return {"status": "error", "message": "Dataset must have date and sales/amount columns.", "predictions": []}

    df = df[[date_col, sales_col]].dropna().copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna()
    
    if len(df) < 3:
        return {"status": "error", "message": "Not enough historical data (minimum 3 records) to generate an accurate forecast.", "predictions": []}

    df = df.sort_values(date_col)
    # Aggregate by date to handle multiple transactions per day
    df = df.groupby(df[date_col].dt.date)[sales_col].sum().reset_index()
    df.columns = [date_col, sales_col]
    
    df["day_index"] = range(len(df))

    X = df[["day_index"]]
    y = df[sales_col].astype(float)

    model = LinearRegression()
    model.fit(X, y)

    future = []
    last_index = int(df["day_index"].iloc[-1])
    last_date = pd.to_datetime(df[date_col].iloc[-1])

    for i in range(1, 8):
        idx = last_index + i
        pred = float(model.predict([[idx]])[0])
        future.append({
            "date": (last_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
            "value": round(max(pred, 0), 2),
            "purpose": "Inventory & Cash Flow Planning",
            "description": "Projected daily performance based on historical trends."
        })

    return {"status": "ok", "message": "Forecast generated successfully using advanced regression.", "predictions": future}

def diagnostics(df=None):
    if df is None:
        df = load_dataset()
    if df.empty:
        return "No dataset found for diagnostics."

    cols = [c.lower() for c in df.columns]
    revenue = 0
    expenses = 0
    
    if "sales" in cols and "expenses" in cols:
        revenue = float(df[next(c for c in df.columns if c.lower() == "sales")].sum())
        expenses = float(df[next(c for c in df.columns if c.lower() == "expenses")].sum())
    elif "amount" in cols and "type" in cols:
        rev_mask = df[next(c for c in df.columns if c.lower() == "type")].astype(str).str.lower().isin(["sale", "revenue", "income"])
        exp_mask = df[next(c for c in df.columns if c.lower() == "type")].astype(str).str.lower().isin(["expense", "cost", "payout"])
        revenue = df[rev_mask]["amount"].sum()
        expenses = df[exp_mask]["amount"].sum()
    else:
        return "Insight: Standardize your 'Type' or 'Sales' columns for deeper financial diagnostics."

    if revenue > 0 and expenses > 0.4 * revenue:
        return "Diagnostic: High overhead detected (over 40% of revenue). Suggestion: Audit variable costs or utility expenses."
    elif revenue > 0:
        return "Diagnostic: Expense-to-revenue ratio is healthy. Maintain current operational efficiency."
    return "Diagnostic: Insufficient financial data for overhead analysis."