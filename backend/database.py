import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from .config import settings

#initialize a thread safe connection
try:
    db_pool = SimpleConnectionPool(
        1, 10,
        host=settings.DB_HOST,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASS
    )
except Exception as e:
    print(f"Failed to initialize database connection pool: {e}")
    db_pool = None

@contextmanager
def get_db_connection():
    """Context manager to lease and safely return database connection"""
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)