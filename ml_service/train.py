import os
import pandas as pd
import numpy as np
import psycopg2
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from imblearn.over_sampling import SMOTE

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "fraudguard_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "postgres")

def load_data():
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    query = """
        SELECT 
            transaction_id,
            user_id,
            product_id,
            amount,
            ip_address,
            device_fingerprint,
            timestamp,
            is_fraud
        FROM transactions
        ORDER BY timestamp ASC;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def engineer_features(df):
    print("Engineering Behavioural insights...")
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek

    user_avg = df.groupby('user_id')['amount'].transform('mean')
    df['amount_to_user_avg_ratio'] = df['amount'] / (user_avg + 1e-5)

    df = df.sort_values(['user_id', 'timestamp'])
    df['tx_count_10m'] = (
        df.groupby('user_id')
        .rolling('10min', on='timestamp')['transaction_id']
        .count()
        .reset_index(level=0, drop=True)
    )

    ip_user_counts = df.groupby('ip_address')['user_id'].nunique().to_dict()
    df['ip_shared_user_count'] = df['ip_address'].map(ip_user_counts)

    df['amount_to_user_avg_ratio'] = df['amount_to_user_avg_ratio'].fillna(1.0)
    df['tx_count_10m'] = df['tx_count_10m'].fillna(1.0)
    df['ip_shared_user_count'] = df['ip_shared_user_count'].fillna(1.0)

    df = df.fillna(0)

    return df

def train():
    print("Fetching training dataset from PostgreSQL...")
    df = load_data()
    df = engineer_features(df)

    feature_cols = [
        'amount',
        'hour',
        'day_of_week',
        'amount_to_user_avg_ratio',
        'tx_count_10m',
        "ip_shared_user_count"
    ]

    X = df[feature_cols]
    y = df['is_fraud']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print("Appling SMOTE oversampling...")
    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)


    print("Training fraud Detection Model (XGBoost)...")
    model = XGBClassifier(
        n_estimators=150, 
        max_depth=6, 
        learning_rate=0.03,  
        random_state=42)
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.35).astype(int)

    print("\n--- Evaluation Results ---")
    print(classification_report(y_test, preds))
    print(f"ROC-AUC Score: {roc_auc_score(y_test, probs):.4f}") 

    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "fraud_model.pkl")

    joblib.dump(model, model_path)
    print(f"Model successfully saved to {model_path}")

if __name__ == "__main__":
    train()