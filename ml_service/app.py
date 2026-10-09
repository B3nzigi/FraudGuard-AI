import os
import joblib
import pandas as pd
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="FraudGuard AI Inference Service")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "fraud_model.pkl")

# Load model artifact at startup
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = None

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "fraudguard_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "postgres")

class TransactionFeatures(BaseModel):
    user_id: str
    amount: float
    ip_address: str
    device_fingerprint: str

def compute_live_features(data: TransactionFeatures):
    """Query recent DB context to generate identical behavioral features used in training."""
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()

        # 1. User average spending
        cur.execute("SELECT AVG(amount) FROM transactions WHERE user_id = %s;", (data.user_id,))
        avg_res = cur.fetchone()[0]
        user_avg = float(avg_res) if avg_res else data.amount
        amount_to_avg_ratio = data.amount / (user_avg + 1e-5)

        # 2. Transaction velocity (last 10 minutes)
        cur.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = %s AND timestamp >= NOW() - INTERVAL '10 minutes';",
            (data.user_id,)
        )
        tx_count_10m = cur.fetchone()[0] + 1  # count including current request

        # 3. IP sharing across users
        cur.execute("SELECT COUNT(DISTINCT user_id) FROM transactions WHERE ip_address = %s;", (data.ip_address,))
        ip_shared_users = cur.fetchone()[0]
        ip_shared_user_count = max(ip_shared_users, 1)

        conn.close()

        # Temporal features based on current UTC time
        now = pd.Timestamp.now()
        
        return pd.DataFrame([{
            'amount': data.amount,
            'hour': now.hour,
            'day_of_week': now.dayofweek,
            'amount_to_user_avg_ratio': amount_to_avg_ratio,
            'tx_count_10m': tx_count_10m,
            'ip_shared_user_count': ip_shared_user_count
        }])
    except Exception as e:
        # Fallback default feature matrix if DB is unreachable
        now = pd.Timestamp.now()
        return pd.DataFrame([{
            'amount': data.amount,
            'hour': now.hour,
            'day_of_week': now.dayofweek,
            'amount_to_user_avg_ratio': 1.0,
            'tx_count_10m': 1.0,
            'ip_shared_user_count': 1.0
        }])

@app.post("/predict")
def predict_fraud(data: TransactionFeatures):
    if model is None:
        raise HTTPException(status_code=500, detail="Model artifact not found. Run train.py first.")

    features_df = compute_live_features(data)
    
    # Generate probability score
    risk_score = float(model.predict_proba(features_df)[0][1])
    is_suspicious = risk_score >= 0.15

    return {
        "risk_score": round(risk_score, 4),
        "is_fraud": is_suspicious,
        "features": features_df.to_dict(orient="records")[0]
    }