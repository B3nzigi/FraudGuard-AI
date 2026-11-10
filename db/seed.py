"""Populate PostgreSQL with realistic transactions scored by the trained model."""
import os
import random
import uuid
import hashlib
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
import psycopg2


random.seed(42)
np.random.seed(42)

FIRST_NAMES = [
    "Amani", "Brian", "Clara", "Daniel", "Esther", "Felix", "Grace", "Hassan", "Irene", "Jabari",
    "Kendi", "Liam", "Miriam", "Noah", "Olive", "Peter", "Quinn", "Ruth", "Sam", "Talia",
    "Umar", "Vera", "Wanjiku", "Xavier", "Yara", "Zuri", "Amara", "David", "Faith", "Kevin",
]
LAST_NAMES = [
    "Abdi", "Barasa", "Chebet", "Dawit", "Eze", "Faruq", "Githinji", "Hassan", "Irungu", "Juma",
    "Kamau", "Limo", "Mwangi", "Njoroge", "Otieno", "Patel", "Qureshi", "Rono", "Shah", "Tesfaye",
    "Udo", "Varga", "Wekesa", "Xaba", "Yusuf", "Zawadi", "Achieng", "Biko", "Cheruiyot", "Dube",
]

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "fraud_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "postgres")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_service", "models", "fraud_model.pkl")


def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)


def populate_missing_user_names(cur):
    cur.execute("SELECT user_id FROM users WHERE first_name IS NULL OR last_name IS NULL ORDER BY user_id")
    users_without_names = cur.fetchall()
    cur.executemany(
        "UPDATE users SET first_name = %s, last_name = %s WHERE user_id = %s",
        [
            (FIRST_NAMES[index % len(FIRST_NAMES)], LAST_NAMES[(index * 7) % len(LAST_NAMES)], str(user_id))
            for index, (user_id,) in enumerate(users_without_names)
        ],
    )
    return len(users_without_names)


def normalize_alert_severities(cur):
    cur.execute(
        """UPDATE alerts SET severity = CASE
                WHEN score >= 0.85 THEN 'Critical'
                WHEN score >= 0.60 THEN 'High'
                WHEN score >= 0.35 THEN 'Medium'
                ELSE 'Low' END"""
    )


def create_missing_prediction_alerts(cur):
    cur.execute(
        """
        INSERT INTO alerts (transaction_id, trigger, severity, score, status)
        SELECT t.transaction_id,
               'Trained model flagged transaction',
               CASE WHEN t.anomaly_score >= 0.85 THEN 'Critical'
                    WHEN t.anomaly_score >= 0.60 THEN 'High'
                    WHEN t.anomaly_score >= 0.35 THEN 'Medium'
                    ELSE 'Low' END,
               LEAST(1.0, GREATEST(0.0, t.anomaly_score)),
               'New'
        FROM transactions t
        WHERE t.is_fraud = 1
          AND NOT EXISTS (
              SELECT 1 FROM alerts a WHERE a.transaction_id = t.transaction_id
          )
        """
    )
    return cur.rowcount


def seed_data(total_transactions=3000):
    model = joblib.load(MODEL_PATH)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM transactions")
            existing_count = cur.fetchone()[0]
            names_added = populate_missing_user_names(cur)
            if existing_count >= total_transactions:
                alert_count = create_missing_prediction_alerts(cur)
                normalize_alert_severities(cur)
                conn.commit()
                print(f"Database already contains {existing_count} transactions; added names to {names_added} users and {alert_count} missing alerts.")
                return

            print("Creating sample users and products...")
            user_ids = []
            for _ in range(200):
                user_id = str(uuid.uuid4())
                index = len(user_ids)
                cur.execute(
                    "INSERT INTO users (user_id, first_name, last_name, email, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING user_id",
                    (user_id, FIRST_NAMES[index % len(FIRST_NAMES)], LAST_NAMES[(index * 7) % len(LAST_NAMES)], f"sample-{user_id.replace('-', '')}@fraudguard.test", datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))),
                )
                user_ids.append(str(cur.fetchone()[0]))

            product_ids = []
            for category in ("Electronics", "Apparel", "Home", "Digital"):
                for _ in range(8):
                    product_id = str(uuid.uuid4())
                    cur.execute(
                        "INSERT INTO products (product_id, product_name, price, category) VALUES (%s, %s, %s, %s) RETURNING product_id",
                        (product_id, f"{category} sample {len(product_ids) + 1}", round(random.uniform(500, 120000), 2), category),
                    )
                    product_ids.append(str(cur.fetchone()[0]))

            print("Generating 90 days of transactions and scoring them with the trained model...")
            start = datetime.now(timezone.utc) - timedelta(days=90)
            rows = []
            for i in range(total_transactions):
                fraud_pattern = random.random() < 0.06
                user_id = random.choice(user_ids)
                amount = float(np.random.exponential(12000) + 500)
                if fraud_pattern and random.random() < 0.55:
                    amount = random.uniform(40000, 250000)
                elif fraud_pattern:
                    amount = random.uniform(150, 1500)
                rows.append({
                    "transaction_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "product_id": random.choice(product_ids),
                    "amount": round(amount, 2),
                    "ip_address": f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
                    "device_fingerprint": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
                    "timestamp": start + timedelta(seconds=i * (90 * 86400 / total_transactions)),
                })

            frame = pd.DataFrame(rows)
            frame["hour"] = frame["timestamp"].dt.hour
            frame["day_of_week"] = frame["timestamp"].dt.dayofweek
            user_average = frame.groupby("user_id")["amount"].transform("mean")
            frame["amount_to_user_avg_ratio"] = frame["amount"] / (user_average + 1e-5)
            frame = frame.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
            frame["tx_count_10m"] = (
                frame.groupby("user_id").rolling("10min", on="timestamp")["transaction_id"]
                .count().reset_index(level=0, drop=True).to_numpy()
            )
            ip_sharing = frame.groupby("ip_address")["user_id"].nunique()
            frame["ip_shared_user_count"] = frame["ip_address"].map(ip_sharing)
            feature_cols = [
                "amount", "hour", "day_of_week", "amount_to_user_avg_ratio",
                "tx_count_10m", "ip_shared_user_count",
            ]
            scores = model.predict_proba(frame[feature_cols].fillna(1.0))[:, 1]
            fraud_predictions = (scores >= 0.15).astype(int)

            insert_rows = []
            for index, record in frame.iterrows():
                insert_rows.append((
                    record.transaction_id, record.user_id, record.product_id,
                    float(record.amount), record.ip_address, record.device_fingerprint,
                    record.timestamp.to_pydatetime(), int(fraud_predictions[index]), float(scores[index]),
                ))
            cur.executemany(
                """INSERT INTO transactions
                   (transaction_id, user_id, product_id, amount, ip_address, device_fingerprint, timestamp, is_fraud, anomaly_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                insert_rows,
            )
            alert_count = create_missing_prediction_alerts(cur)
            normalize_alert_severities(cur)
        conn.commit()
        predicted = int(fraud_predictions.sum())
        print(f"Inserted {len(rows)} transactions; model predicted {predicted} as suspicious and created {alert_count} alerts.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_data()
