from fastapi import FastAPI, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .schemas import CheckoutRequest, LoginRequest, Token
from .database import get_db_connection
from psycopg2.extras import RealDictCursor
from passlib.context import CryptContext
from datetime import datetime
import bcrypt

# passlib 1.7.4 looks for bcrypt.__about__, which bcrypt 4.x removed
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("about", (), {"__version__": bcrypt.__version__})
from .schemas import RegisterRequest
from pydantic import BaseModel
from typing import List
from .config import settings
from .security import create_access_token, get_current_user
import requests
import jwt

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

# --- Database Alert Helper Functions ---
def fetch_all_alerts_db(limit=50):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    a.alert_id, 
                    a.transaction_id, 
                    a.trigger, 
                    a.severity, 
                    a.score, 
                    a.status, 
                    a.created_at,
                    t.user_id,
                    t.amount,
                    t.ip_address,
                    t.device_fingerprint
                FROM alerts a
                LEFT JOIN transactions t ON a.transaction_id = t.transaction_id
                ORDER BY a.created_at DESC 
                LIMIT %s;
            """, (limit,))
            return cur.fetchall()

def insert_alert_db(transaction_id, trigger, severity, score):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO alerts (transaction_id, trigger, severity, score, status)
                VALUES (%s, %s, %s, %s, 'New')
                RETURNING alert_id, transaction_id, trigger, severity, score, status, created_at;
            """, (transaction_id, trigger, severity, score))
            new_alert = cur.fetchone()
            conn.commit()
            return dict(new_alert)

def update_alert_status_db(alert_id: str, new_status: str):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE alerts 
                SET status = %s 
                WHERE alert_id = %s
                RETURNING alert_id, status;
            """, (new_status, alert_id))
            updated = cur.fetchone()
            conn.commit()
            return dict(updated) if updated else None


@app.get("/")
def read_root():
    return {"message": "Welcome to the FraudGuardAI core API engine backend."}

@app.post("/api/v1/auth/login", response_model=Token)
def login(payload: LoginRequest):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, password_hash, email FROM users WHERE email = %s;", (payload.email,))
            user = cur.fetchone()

    if user and verify_password(payload.password, user[1]):
        token = create_access_token(data={"sub": str(user[0]), "email": user[2]})
        return {"access_token": token, "token_type": "bearer"}

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

@app.post("/api/v1/checkout", status_code=201)
async def checkout(transaction: CheckoutRequest):
    fraud_score = 0.15
    is_flagged = 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO transactions (user_id, product_id, amount, ip_address, device_fingerprint) 
                   VALUES (%s, %s, %s, %s, %s) RETURNING transaction_id;""",
                (str(transaction.user_id), str(transaction.product_id), transaction.amount, transaction.ip_address, transaction.device_fingerprint)
            )
            transaction_id = cur.fetchone()[0]
            conn.commit()
            
    # --- ML Microservice call ---
    ml_service_url = "http://127.0.0.1:8000/predict"
    
    try:
        response = requests.post(
            ml_service_url,
            json={
                "user_id": str(transaction.user_id),
                "amount": float(transaction.amount),
                "ip_address": transaction.ip_address,
                "device_fingerprint": transaction.device_fingerprint
            },
            timeout=2.0
        )
        
        if response.status_code == 200:
            ml_data = response.json()
            fraud_score = ml_data.get("risk_score", 0.15)
            is_flagged = 1 if ml_data.get("is_fraud", False) else 0

    except requests.exceptions.RequestException:
        print("WARNING: ML Microservice is offline! Using fallback scoring.")
        fraud_score = 0.15
        is_flagged = 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE transactions SET is_fraud = %s WHERE transaction_id = %s;",
                (is_flagged, transaction_id)
            )
            conn.commit()

    # Persist and Broadcast Alert if Triggered
    if is_flagged == 1 or fraud_score >= 0.75:
        trigger_reason = "Automated ML Anomaly Detection"
        severity = "Critical" if fraud_score >= 0.85 else "High"
        
        saved_alert = insert_alert_db(
            transaction_id=transaction_id,
            trigger=trigger_reason,
            severity=severity,
            score=float(fraud_score)
        )
        
        new_alert_payload = {
            "type": "NEW_ALERT",
            "data": {
                "id": str(saved_alert["alert_id"]),
                "timestamp": saved_alert["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                "trigger": saved_alert["trigger"],
                "userId": str(transaction.user_id),
                "amount": f"KES {transaction.amount:,.2f}",
                "ip": transaction.ip_address,
                "location": "Live System Stream",
                "severity": saved_alert["severity"],
                "score": round(saved_alert["score"], 2),
                "status": saved_alert["status"],
                "device": transaction.device_fingerprint
            }
        }
        await manager.broadcast(new_alert_payload)
    
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
            cur.execute("SELECT user_id FROM users WHERE email = %s;", (payload.email,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")

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
    block_vpn: bool = Query(False),
    current_user: dict = Depends(get_current_user)
):
    base_exposure = 5_450_000 if timeframe == "7d" else 1_250_000
    mpesa_factor = 0.75 if enforce_mpesa else 1.0
    vpn_factor = 0.85 if block_vpn else 1.0
    adjusted_exposure = int(round(base_exposure * (1.5 - cutoff) * mpesa_factor * vpn_factor))

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

class StatusUpdatePayload(BaseModel):
    status: str

@app.get("/api/v1/alerts")
def get_alerts(current_user: dict = Depends(get_current_user)):
    """Fetch recent alerts directly from PostgreSQL alerts table."""
    rows = fetch_all_alerts_db()
    return [
        {
            "id": str(row["alert_id"]),
            "timestamp": row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if row["created_at"] else "",
            "trigger": row["trigger"],
            "severity": row["severity"],
            "score": row["score"],
            "status": row["status"],
            "transaction_id": str(row["transaction_id"]) if row["transaction_id"] else None,
            "userId": str(row["user_id"]) if row["user_id"] else "Unknown",
            "amount": f"KES {float(row['amount']):,.2f}" if row["amount"] is not None else "KES 0.00",
            "ip": str(row["ip_address"]) if row["ip_address"] else "Unknown",
            "location": "Live System Stream",
            "device": row["device_fingerprint"] if row["device_fingerprint"] else "Unknown"
        }
        for row in rows
    ]

@app.patch("/api/v1/alerts/{alert_id}/status")
def update_alert_status(
    alert_id: str,
    payload: StatusUpdatePayload,
    current_user: dict = Depends(get_current_user),
):
    """Update alert review status directly in PostgreSQL."""
    updated = update_alert_status_db(alert_id, payload.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    return {"message": "Status updated successfully", "alert": updated}

# Manage active user WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting message: {e}")

manager = ConnectionManager()

@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket, token: str = Query(...)):
    try: 
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except jwt.PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/ready")
def ready():
    try:
        with get_db_connection() as conn:
            conn.cursor().execute("SELECT 1")
        return {"ready": True}
    except:
        raise HTTPException(503, "DB unavailable")