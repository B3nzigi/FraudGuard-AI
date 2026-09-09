from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from .schemas import CheckoutRequest, LoginRequest, Token
from .database import get_db_connection
from passlib.context import CryptContext
from .schemas import RegisterRequest
from pydantic import BaseModel
import requests

app = FastAPI(title="FraudGuardAI Core API")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Enable CORS so your React frontend can talk to your API safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the FraudGuardAI core API engine backend."}

@app.post("/api/v1/auth/login", response_model=Token)
def login(payload: LoginRequest):
    # Authentication logic
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            #looks at user email
            cur.execute("SELECT user_id, password_hash FROM users WHERE email = %s;", (payload.email,))
            user = cur.fetchone()

    #check if user and password are correct
    if user and verify_password(payload.password, user[1]):
        return {"access_token": f"mock_jwt_token_for_user_{user[0]}", "token_type": "bearer"}

    raise HTTPException(status_code=401, detail="Invalid Credentials")

@app.post("/api/v1/checkout", status_code=201)
def checkout(transaction: CheckoutRequest):
    # 1. Define safe default values right away to make VS Code happy!
    fraud_score = 0.15
    is_flagged = 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Persist transaction data to database
            cur.execute(
                """INSERT INTO transactions (user_id, product_id, amount, ip_address, device_fingerprint) 
                   VALUES (%s, %s, %s, %s, %s) RETURNING transaction_id;""",
                (str(transaction.user_id), str(transaction.product_id), transaction.amount, transaction.ip_address, transaction.device_fingerprint)
            )
            transaction_id = cur.fetchone()[0]
            conn.commit()
            
    # --- ML Microservice call ---
    ml_service_url = "http://127.0.0.1:8001/predict"
    
    try:
        response = requests.post(
            ml_service_url,
            json={
                "amount": float(transaction.amount),
                "ip_address": transaction.ip_address,
                "device_fingerprint": transaction.device_fingerprint
            },
            timeout=2.0
        )
        
        if response.status_code == 200:
            ml_data = response.json()
            fraud_score = ml_data.get("fraud_score", 0.0)
            is_flagged = 1 if ml_data.get("is_flagged", False) else 0
        else:
            # Fall back to default if server error
            fraud_score = 0.15
            is_flagged = 0
            
    except requests.exceptions.RequestException:
        print("WARNING: ML Microservice is offline! Using fallback scoring.")
        # Fall back to default if offline
        fraud_score = 0.15
        is_flagged = 0

    # optional: update DB with real fraud score we just received
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE transactions SET is_fraud = %s WHERE transaction_id = %s;",
                (is_flagged, transaction_id)
            )
            conn.commit()
    
    return {
        "status": "processed",
        "transaction_id": transaction_id,
        "fraud_score": fraud_score,
        "action": "allow" if not is_flagged else "review"
    }

@app.get("/api/v1/transactions")
def get_transactions(limit: int = 20, offset: int = 0):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT transaction_id, user_id, amount, timestamp, is_fraud FROM transactions ORDER BY timestamp DESC LIMIT %s OFFSET %s;",
                (limit, offset)
            )
            rows = cur.fetchall()
            
    return [{"id": r[0], "user_id": r[1], "amount": float(r[2]), "timestamp": r[3], "is_fraud": r[4]} for r in rows]

@app.post("/api/v1/auth/register", status_code=201)
def register(payload: RegisterRequest):
    hashed_pwd = hash_password(payload.password)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            #check is user exists
            cur.execute("SELECT user_id FROM users WHERE email = %s;", (payload.email,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")

            #Create new user
            cur.execute(
                """INSERT INTO users (first_name, last_name, email, password_hash)
                   VALUES (%s, %s, %s, %s) RETURNING user_id, email;""",
                (payload.first_name, payload.last_name, payload.email, hashed_pwd)
            )
            new_user = cur.fetchone()
            conn.commit()

    return {
        "status": "success",
        "message": "User registered Successfully",
        "user": {
            "id": new_user[0],
            "email": new_user[1]
        }
    }

@app.get("/api/v1/forecast")
def get_ml_forecast(
    timeframe: str = Query("7d", description="Timeframe: '24h' or '7d'"),
    cutoff: float = Query(0.75, description="Risk threshold cuttoff between 0.50 and 0.95"),
    enforce_mpesa: bool = Query(True),
    block_vpn: bool = Query(False)
):
    #Base financial exposure in ksh
    base_exposure = 5_450_000 if timeframe == "7d" else 1_250_000

    #Dynamic mitigation calc based on simulator rules
    mpesa_factor = 0.75 if enforce_mpesa else 1.0
    vpn_factor = 0.85 if block_vpn else 1.0
    adjusted_exposure = int(round(base_exposure * (1.5 - cutoff) * mpesa_factor * vpn_factor))

    #generate chart dataset based on selected timeframe
    if timeframe == "7d":
        chart_data = [
            {"day": "Mon", "actual": 120, "forecast": 115, "upperBound": 140, "lowerBound": 90},
            {"day": "Tue", "actual": 150, "forecast": 145, "upperBound": 175, "lowerBound": 115},
            {"day": "Wed", "actual": 180, "forecast": 190, "upperBound": 220, "lowerBound": 160},
            {"day": "Thu", "actual": 210, "forecast": 205, "upperBound": 240, "lowerBound": 170},
            {"day": "Fri", "actual": 310, "forecast": 340, "upperBound": 400, "lowerBound": 280},
            {"day": "Sat", "actual": None, "forecast": 490, "upperBound": 580, "lowerBound": 410},
            {"day": "Sun", "actual": None, "forecast": 420, "upperBound": 510, "lowerBound": 330},
        ]
    else:
        chart_data = [
            {"day": "00:00", "actual": 15, "forecast": 14, "upperBound": 22, "lowerBound": 8},
            {"day": "04:00", "actual": 42, "forecast": 40, "upperBound": 55, "lowerBound": 30},
            {"day": "08:00", "actual": 18, "forecast": 22, "upperBound": 32, "lowerBound": 12},
            {"day": "12:00", "actual": 28, "forecast": 30, "upperBound": 42, "lowerBound": 20},
            {"day": "16:00", "actual": 65, "forecast": 70, "upperBound": 90, "lowerBound": 50},
            {"day": "20:00", "actual": None, "forecast": 110, "upperBound": 140, "lowerBound": 85},
            {"day": "23:59", "actual": None, "forecast": 45, "upperBound": 60, "lowerBound": 30},
        ]

    return {
        "timeframe": timeframe,
        "riskCutoff": cutoff,
        "projectedSurge": "+24.6%",
        "adjustedExposureKES": adjusted_exposure,
        "peakWindow": "Sat 02:00 - 06:00 EAT" if timeframe == "7d" else "16:00 - 20:00 EAT",
        "modelDrift": "0.03 (Stable)",
        "chartData": chart_data,
        "attackVectors": [
            {"label": "M-pesa SIM Swap / Account takeover", "percentage": 54, "level": "danger"},
            {"label": "Carding & Bot Velocity Attacks", "percentage": 28, "level": "warning"},
            {"label": "Promo Code / Referral Exploits", "percentage": 18, "level": "info"}
        ]
    }

#inmemory alerts dataset
mock_alerts_db = [
    {
        "id": "ALT-8801",
        "timestamp": "2026-07-30 11:42:15",
        "trigger": "Velocity Spike (5 txs / 60s)",
        "userId": "usr_9921",
        "amount": "$2,450.00",
        "ip": "185.220.101.5",
        "location": "Frankfurt, DE",
        "severity": "Critical",
        "score": 0.94,
        "status": "New",
        "device": "Chrome / Linux (TOR Exit Node)"
    },
    {
        "id": "ALT-8802",
        "timestamp": "2026-07-30 11:15:02",
        "trigger": "Carding Pattern Detection",
        "userId": "usr_1042",
        "amount": "$1.00",
        "ip": "104.28.19.88",
        "location": "Ashburn, US",
        "severity": "High",
        "score": 0.88,
        "status": "Under Investigation",
        "device": "Safari / iOS 17.4"
    },
    {
        "id": "ALT-8803",
        "timestamp": "2026-07-30 10:55:40",
        "trigger": "Anonymous Proxy / VPN Usage",
        "userId": "usr_5190",
        "amount": "$890.00",
        "ip": "172.56.21.9",
        "location": "Dallas, US",
        "severity": "Medium",
        "score": 0.65,
        "status": "New",
        "device": "Firefox / Windows 11"
    },
    {
        "id": "ALT-8804",
        "timestamp": "2026-07-30 09:30:11",
        "trigger": "Geographic Impossible Speed",
        "userId": "usr_3311",
        "amount": "$4,120.00",
        "ip": "190.211.8.44",
        "location": "Bogota, CO",
        "severity": "Critical",
        "score": 0.96,
        "status": "New",
        "device": "Edge / Windows 10"
    },
    {
        "id": "ALT-8805",
        "timestamp": "2026-07-30 08:12:00",
        "trigger": "Unusual High Amount for User",
        "userId": "usr_7701",
        "amount": "$7,800.00",
        "ip": "64.233.160.1",
        "location": "Mountain View, US",
        "severity": "Low",
        "score": 0.42,
        "status": "Resolved - Approved",
        "device": "Chrome / macOS 14"
    }
]

class StatusUpdatePayload(BaseModel):
    status: str

@app.get("/api/v1/alerts")
def get_alerts():
    return mock_alerts_db

@app.patch("/api/v1/alerts/{alert_id}/status")
def update_alert_status(alert_id: str, payload: StatusUpdatePayload):
    for alert in mock_alerts_db:
        if alert["id"] == alert_id:
            alert["status"] = payload.status
            return {"message": "Status updated successfully", "alert": alert}
        raise HTTPException(status_code=404, detail="Alert not found")