import os
import random
import uuid
import psycopg2
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "fraud_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "postgres")

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)

def seed_data():
    conn = get_db_connection()
    cur = conn.cursor()

    print("Seeding Users and Products...")

    #create base users
    user_ids = []
    for _ in range(500):
        uid = str(uuid.uuid4())
        user_ids.append(uid)
        cur.execute(
            "INSERT INTO users (user_id, email, created_at) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;",
            (uid, fake.unique.email(), fake.date_time_this_year())
        )

    #create base products
    product_ids = []
    categories = ['Electronics', 'Apparel', 'Home', 'Digital']
    for _ in range(50):
        pid = str(uuid.uuid4())
        product_ids.append(pid)
        cur.execute(
            "INSERT INTO products (product_id, product_name, price, category) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;",
            (pid, fake.catch_phrase(), round(random.uniform(10.0, 1200.0), 2), random.choice(categories))
        )

    conn.commit()
    print("Generating Transactions(including intentional fraud anomalies)...")

    #Generate transactions
    total_transactions = 10000
    start_date = datetime.now() - timedelta(days=90)

    for i in range(total_transactions):
        user_id = random.choice(user_ids)
        product_id = random.choice(product_ids)

        #time progression over 90 days
        timestamp = start_date + timedelta(seconds=i * (90 * 86400 / total_transactions))

        #Default baseline
        amount = round(random.uniform(15.0, 250,0), 2)
        ip_address = fake.ipv4()
        device_fingerprint = fake.sha256()
        is_fraud = 0

        #Inject Anomalies
        dice_roll = random.random()
        if dice_roll < 0.015:
            is_fraud = 1
            fraud_type = random.choice(['velocity', 'whale', 'ip_hop'])

            if fraud_type == 'whale':
                #massive transaction from no where
                amount = round(random.uniform(5000.0, 15000.0), 2)

            elif fraud_type == 'velocity':
                #rapid repeated transactions
                timestamp = timestamp - timedelta(second=random.randint(1, 5))
                amount = round(random.uniform(10.0, 50.0), 2)

            elif fraud_type == 'ip_hop':
                #hosting multiple proxies
                ip_address = f"192.168.{random.randint(200, 254)}.{random.randint(1, 254)}"

        cur.execute(
            """INSERT INTO transactions
               (user_id, product_id, amount, ip_address, device_fingerprint, timestamp, is_fraud)
            VALUES (%s, %s, %s, %s, %s, %s, %s);"""
        )

        #batch commits to avoid hitting disk 10,000 times individually
        if i % 1000 == 0:
            conn.commit()
    
    conn.commit()
    cur.close()
    conn.close()
    print("The Database was completely seeded with standard profiles and anomalies!")

if __name__ == "__main__":
    seed_data()