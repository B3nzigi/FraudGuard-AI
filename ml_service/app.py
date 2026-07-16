from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI(title="FraudGuardAI ML Predictor")

#fields the model need sto make predictions
class TransactionFeatures(BaseModel):
    amount: float
    ip_address: str
    device_fingerprint: str

#prediction endpoint
@app.post("/predict")
def predict_fraud(data: TransactionFeatures):
    #simulated machine learning interface logic
    #in production you would do: model.predict_prob

    risk_score = 0.05 # base low

    #Rule 1: high transaction amount flags higher risk
    if data.amount > 5000:
        risk_score += 0.45
    elif data.amount > 1000:
        risk_score += 0.25

    #Rule 2: random simulations= of anomalous network
    if "unknown" in data.device_fingerprint.lower() or not data.ip_address:
        risk_score += 0.30

    #add tiny bit of random variations to make the ml score look dynamic
    risk_score += random.uniform(-0.02, 0.05)

    #Cap risk score bten 0.0 and 1.0
    final_score = float(max(0.0, min(1.0, risk_score)))

    #flag transaction as suspiscious if the score is greater than 70%
    is_suspicious = final_score > 0.70

    return {
        "fraud_score": round(final_score, 4),
        "is_flagged": is_suspicious,
        "model_version": "v1.0-anomaly-detector"
    }