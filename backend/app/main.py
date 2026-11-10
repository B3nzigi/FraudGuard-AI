from fastapi import FastAPI, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .schemas import CheckoutRequest, LoginRequest, Token
from .database import get_db_connection
from psycopg2.extras import RealDictCursor
from passlib.context import CryptContext
from datetime import datetime
import os
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
def fetch_all_alerts_db(limit=500):
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
                    t.device_fingerprint,
                    t.timestamp AS transaction_timestamp,
                    t.anomaly_score,
                    u.first_name,
                    u.last_name,
                    COALESCE(user_stats.avg_amount, 0) AS user_avg_amount,
                    COALESCE(velocity.tx_count_10m, 0) AS tx_count_10m,
                    COALESCE(ip_stats.shared_user_count, 0) AS ip_shared_user_count
                FROM alerts a
                LEFT JOIN transactions t ON a.transaction_id = t.transaction_id
                LEFT JOIN users u ON u.user_id = t.user_id
                LEFT JOIN LATERAL (
                    SELECT AVG(amount) AS avg_amount FROM transactions
                    WHERE user_id = t.user_id
                ) user_stats ON TRUE
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS tx_count_10m FROM transactions
                    WHERE user_id = t.user_id
                      AND timestamp BETWEEN t.timestamp - INTERVAL '10 minutes' AND t.timestamp
                ) velocity ON TRUE
                LEFT JOIN LATERAL (
                    SELECT COUNT(DISTINCT user_id) AS shared_user_count FROM transactions
                    WHERE ip_address = t.ip_address
                ) ip_stats ON TRUE
                ORDER BY a.created_at DESC 
                LIMIT %s;
            """, (limit,))
            return cur.fetchall()


def severity_from_score(score: float) -> str:
    if score >= 0.85:
        return "Critical"
    if score >= 0.60:
        return "High"
    if score >= 0.35:
        return "Medium"
    return "Low"


def explain_alert(row):
    score = float(row["score"] or 0)
    amount = float(row["amount"] or 0)
    average = float(row["user_avg_amount"] or 0)
    ratio = amount / average if average > 0 else 1.0
    velocity = int(row["tx_count_10m"] or 0)
    shared_users = int(row["ip_shared_user_count"] or 0)

    signals = []
    if amount >= 40000:
        signals.append(f"high transaction value (KES {amount:,.2f})")
    if ratio >= 3:
        signals.append(f"spend is {ratio:.1f}× this account's average")
    if velocity >= 3:
        signals.append(f"{velocity} transactions from this account in 10 minutes")
    if shared_users >= 3:
        signals.append(f"IP address is shared by {shared_users} accounts")

    explanation = f"The model assigned {score:.1%} risk, above its 15% flagging threshold."
    if signals:
        explanation += " Observed signals: " + "; ".join(signals) + "."
    else:
        explanation += " The model evaluated transaction value, time, account spending history, transaction velocity, and IP sharing."
    return explanation, ratio

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

    # Existing seeded accounts may not have a password hash yet.
    if user and user[1] and verify_password(payload.password, user[1]):
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
                   VALUES (%s, %s, %s, %s, %s) RETURNING transaction_id, timestamp;""",
                (str(transaction.user_id), str(transaction.product_id), transaction.amount, transaction.ip_address, transaction.device_fingerprint)
            )
            transaction_id, created_at = cur.fetchone()
            conn.commit()
            
    # ML Microservice call
    ml_service_url = f"{os.getenv('ML_SERVICE_URL', 'http://localhost:8001').rstrip('/')}/predict"
    
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
                "UPDATE transactions SET is_fraud = %s, anomaly_score = %s WHERE transaction_id = %s;",
                (is_flagged, fraud_score, transaction_id)
            )
            conn.commit()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT first_name, last_name FROM users WHERE user_id = %s", (str(transaction.user_id),))
            user_name_row = cur.fetchone()
    user_name = " ".join(part for part in (user_name_row or (None, None)) if part) or "Unknown account"
    transaction_action = "Review" if is_flagged or fraud_score >= 0.75 else "Allowed"
    await manager.broadcast({
        "type": "NEW_TRANSACTION",
        "data": {
            "id": str(transaction_id),
            "userId": str(transaction.user_id),
            "userName": user_name,
            "amount": float(transaction.amount),
            "timestamp": created_at.isoformat(),
            "ip": transaction.ip_address,
            "score": float(fraud_score),
            "is_fraud": bool(is_flagged),
            "status": transaction_action,
        },
    })

    # Persist and Broadcast Alert if Triggered
    if is_flagged == 1 or fraud_score >= 0.75:
        trigger_reason = "Automated ML Anomaly Detection"
        severity = severity_from_score(float(fraud_score))
        
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
                "transaction_id": str(saved_alert["transaction_id"]),
                "timestamp": saved_alert["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                "trigger": saved_alert["trigger"],
                "userId": str(transaction.user_id),
                "userName": user_name,
                "reason": f"The model assigned {float(fraud_score):.1%} risk, above its 15% flagging threshold.",
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
def get_transactions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT t.transaction_id, t.user_id, t.amount, t.timestamp, t.is_fraud,
                          t.anomaly_score, t.ip_address, u.first_name, u.last_name
                   FROM transactions t
                   LEFT JOIN users u ON u.user_id = t.user_id
                   ORDER BY t.timestamp DESC LIMIT %s OFFSET %s;""",
                (limit, offset)
            )
            rows = cur.fetchall()
            
    return [{
        "id": str(r[0]),
        "user_id": str(r[1]),
        "user_name": " ".join(part for part in (r[7], r[8]) if part) or "Unknown account",
        "amount": float(r[2]),
        "timestamp": r[3].isoformat() if r[3] else None,
        "is_fraud": int(r[4] or 0),
        "risk_score": float(r[5] or 0),
        "ip_address": str(r[6]) if r[6] else "Unknown",
        "action": "Review" if int(r[4] or 0) or float(r[5] or 0) >= 0.75 else "Allowed",
    } for r in rows]


@app.get("/api/v1/overview")
def get_overview(current_user: dict = Depends(get_current_user)):
    """Return current database totals from transactions scored by the fraud model."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE anomaly_score > 0),
                    COUNT(*) FILTER (WHERE is_fraud = 1),
                    COUNT(*) FILTER (WHERE is_fraud = 0)
                FROM transactions
            """)
            inspected, flagged, cleared = cur.fetchone()
    return {
        "total_inspected": inspected,
        "total_flagged": flagged,
        "total_cleared": cleared,
    }

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
    interval = "7 days" if timeframe == "7d" else "24 hours"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE timestamp >= NOW() - (%s)::interval
                        AND anomaly_score >= %s),
                    COUNT(*) FILTER (WHERE timestamp < NOW() - (%s)::interval
                        AND timestamp >= NOW() - ((%s)::interval * 2)
                        AND anomaly_score >= %s),
                    COALESCE(SUM(amount) FILTER (WHERE timestamp >= NOW() - (%s)::interval
                        AND anomaly_score >= %s), 0),
                    AVG(anomaly_score) FILTER (WHERE timestamp >= NOW() - (%s)::interval),
                    AVG(anomaly_score) FILTER (WHERE timestamp < NOW() - (%s)::interval
                        AND timestamp >= NOW() - ((%s)::interval * 2))
                FROM transactions
                WHERE timestamp >= NOW() - ((%s)::interval * 2)
                """,
                (interval, cutoff, interval, interval, cutoff, interval, cutoff,
                 interval, interval, interval, interval),
            )
            recent_count, previous_count, recent_exposure, recent_score, previous_score = cur.fetchone()
            cur.execute(
                """
                SELECT EXTRACT(HOUR FROM timestamp)::int AS hour, COUNT(*)
                FROM transactions
                WHERE timestamp >= NOW() - (%s)::interval AND anomaly_score >= %s
                GROUP BY hour ORDER BY COUNT(*) DESC, hour LIMIT 1
                """,
                (interval, cutoff),
            )
            peak = cur.fetchone()
            cur.execute(
                """
                WITH scored AS (
                    SELECT
                        amount,
                        COUNT(*) OVER (
                            PARTITION BY user_id ORDER BY timestamp
                            RANGE BETWEEN INTERVAL '10 minutes' PRECEDING AND CURRENT ROW
                        ) AS tx_count_10m
                    FROM transactions
                    WHERE timestamp >= NOW() - (%s)::interval AND anomaly_score >= %s
                ), categorized AS (
                    SELECT CASE
                        WHEN amount BETWEEN 150 AND 1500 OR tx_count_10m >= 3 THEN 'carding_velocity'
                        WHEN amount >= 40000 THEN 'high_value'
                        ELSE 'other'
                    END AS vector
                    FROM scored
                )
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER (WHERE vector = 'high_value'),
                    COUNT(*) FILTER (WHERE vector = 'carding_velocity'),
                    COUNT(*) FILTER (WHERE vector = 'other')
                FROM categorized
                """,
                (interval, cutoff),
            )
            total_vectors, high_value_count, carding_count, other_count = cur.fetchone()

    vector_counts = [high_value_count, carding_count, other_count]
    vector_percentages = [int(count * 100 / total_vectors) if total_vectors else 0 for count in vector_counts]
    if total_vectors:
        vector_percentages[max(range(len(vector_counts)), key=vector_counts.__getitem__)] += 100 - sum(vector_percentages)

    surge = ((recent_count - previous_count) / previous_count * 100) if previous_count else (100.0 if recent_count else 0.0)
    mpesa_factor = 0.75 if enforce_mpesa else 1.0
    vpn_factor = 0.85 if block_vpn else 1.0
    adjusted_exposure = int(round(float(recent_exposure or 0) * (1 + max(surge, 0) / 100) * mpesa_factor * vpn_factor))
    peak_hour = peak[0] if peak else None
    peak_window = (
        f"{peak_hour:02d}:00 - {(peak_hour + 4) % 24:02d}:00 EAT" if peak_hour is not None
        else "Insufficient scored activity"
    )
    drift = abs(float(recent_score or 0) - float(previous_score or 0))
    drift_label = "Stable" if drift < 0.05 else "Watch" if drift < 0.15 else "Elevated"

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
        "projectedSurge": f"{'+' if surge >= 0 else ''}{surge:.1f}%",
        "adjustedExposureKES": adjusted_exposure,
        "peakWindow": peak_window,
        "modelDrift": f"{drift:.2f} ({drift_label})",
        "chartData": chart_data,
        "totalScoredFlags": total_vectors,
        "attackVectors": [
            {"label": "High-value spend spikes", "count": high_value_count, "percentage": vector_percentages[0], "level": "danger"},
            {"label": "Low-value carding & velocity", "count": carding_count, "percentage": vector_percentages[1], "level": "warning"},
            {"label": "Other scored anomalies", "count": other_count, "percentage": vector_percentages[2], "level": "info"}
        ]
    }

class StatusUpdatePayload(BaseModel):
    status: str

@app.get("/api/v1/alerts")
def get_alerts(current_user: dict = Depends(get_current_user)):
    """Fetch recent alerts directly from PostgreSQL alerts table."""
    rows = fetch_all_alerts_db()
    alerts = []
    for row in rows:
        reason, amount_ratio = explain_alert(row)
        full_name = " ".join(part for part in (row["first_name"], row["last_name"]) if part)
        alerts.append({
            "id": str(row["alert_id"]),
            "timestamp": row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if row["created_at"] else "",
            "trigger": row["trigger"],
            "severity": row["severity"],
            "score": float(row["score"] or 0),
            "status": row["status"],
            "transaction_id": str(row["transaction_id"]) if row["transaction_id"] else None,
            "userId": str(row["user_id"]) if row["user_id"] else "Unknown",
            "userName": full_name or "Unknown account",
            "amount": f"KES {float(row['amount']):,.2f}" if row["amount"] is not None else "KES 0.00",
            "ip": str(row["ip_address"]) if row["ip_address"] else "Unknown",
            "location": "Live System Stream",
            "device": row["device_fingerprint"] if row["device_fingerprint"] else "Unknown",
            "transactionTimestamp": row["transaction_timestamp"].strftime("%Y-%m-%d %H:%M:%S") if row["transaction_timestamp"] else "Unknown",
            "reason": reason,
            "modelFeatures": [
                {"label": "Amount-to-account-average ratio", "value": f"{amount_ratio:.2f}×"},
                {"label": "Transactions in 10 minutes", "value": int(row["tx_count_10m"] or 0)},
                {"label": "Accounts sharing this IP", "value": int(row["ip_shared_user_count"] or 0)},
                {"label": "Model anomaly score", "value": f"{float(row['anomaly_score'] or row['score'] or 0):.4f}"},
            ],
        })
    return alerts

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
