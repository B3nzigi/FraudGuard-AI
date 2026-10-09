import os
import pandas as pd
import numpy as np
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from imblearn.over_sampling import SMOTE

def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), "transactions_dataset.csv")
    print(f"Loading training dataset from {csv_path}...")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset file not found at {csv_path}. Run generate_data.py first!")
        
    df = pd.read_csv(csv_path)
    return df

def engineer_features(df):
    print("Engineering Behavioural insights...")

    if 'ip' in df.columns and 'ip_address' not in df.columns:
        df = df.rename(columns={'ip': 'ip_address'})

    #ISO timestamps to CSV timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek

    #Amount to user average ratio
    user_avg = df.groupby('user_id')['amount'].transform('mean')
    df['amount_to_user_avg_ratio'] = df['amount'] / (user_avg + 1e-5)

    #Transaction count in the last 10 minutes
    df = df.sort_values(['user_id', 'timestamp'])
    df['tx_count_10m'] = (
        df.groupby('user_id')
        .rolling('10min', on='timestamp')['transaction_id']
        .count()
        .reset_index(level=0, drop=True)
    )

    #IP shared user count
    ip_user_counts = df.groupby('ip_address')['user_id'].nunique().to_dict()
    df['ip_shared_user_count'] = df['ip_address'].map(ip_user_counts)

    df['amount_to_user_avg_ratio'] = df['amount_to_user_avg_ratio'].fillna(1.0)
    df['tx_count_10m'] = df['tx_count_10m'].fillna(1.0)
    df['ip_shared_user_count'] = df['ip_shared_user_count'].fillna(1.0)

    df = df.fillna(0)

    return df

def train():
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
    model.fit(X_train_res, y_train_res)

    probs = model.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.15).astype(int)

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