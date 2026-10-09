import pandas as pd
import numpy as np
import uuid
from datetime import datetime, timedelta

def generate_csv_dataset(filename="transactions_dataset.csv", num_records=5000):
    np.random.seed(42)

    users = [str(uuid.uuid4()) for _ in range(200)]
    products = [str(uuid.uuid4()) for _ in range(25)]
    
    # Common shared pool of IPs and Devices across BOTH normal and fraud users
    ips = [f"192.168.{np.random.randint(1, 255)}.{np.random.randint(1, 255)}" for _ in range(80)]
    devices = [f"fp_device_{i}" for i in range(120)]

    records = []
    base_time = datetime(2026, 7, 1)

    for i in range(num_records):
        user_id = np.random.choice(users)
        product_id = np.random.choice(products)
        
        # Fraud rate (~4%)
        is_fraud = 1 if np.random.rand() < 0.04 else 0

        # Sample IP and Device from shared pool (no deterministic leakage)
        ip = np.random.choice(ips)
        device = np.random.choice(devices)

        if is_fraud:
            # Fraud scenarios: 50% spending spike relative to standard, 50% low amount carding tests
            if np.random.rand() < 0.5:
                amount = round(np.random.uniform(40000.0, 250000.0), 2)
            else:
                amount = round(np.random.uniform(150.0, 1500.0), 2)
            anomaly_score = round(np.random.uniform(0.70, 0.98), 2)
        else:
            # Normal purchases averaging ~12,000 KES
            amount = round(np.random.exponential(scale=12000.0) + 500.0, 2)
            anomaly_score = round(np.random.uniform(0.01, 0.25), 2)

        timestamp = base_time + timedelta(seconds=i * 120 + np.random.randint(0, 45))

        records.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": user_id,
            "product_id": product_id,
            "amount": amount,
            "ip": ip,
            "device_fingerprint": device,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S+00:00"),
            "is_fraud": is_fraud,
            "anomaly_score": anomaly_score,
        })

    df = pd.DataFrame(records)
    df.to_csv(filename, index=False)
    print(f"Successfully generated {num_records} realistic KES transaction records in '{filename}'.")

if __name__ == "__main__":
    generate_csv_dataset()