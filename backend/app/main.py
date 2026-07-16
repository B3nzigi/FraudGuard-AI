from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from .schemas import CheckoutRequest, LoginRequest, Token
from .database import get_db_connection
from passlib.context import CryptContext
from .schemas import RegisterRequest
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