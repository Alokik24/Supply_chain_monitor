import os
import psycopg2
from psycopg2.extras import RealDictCursor
import redis


# 1. Fetch our hidden environment secrets from the container RAM
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secret_pass")
DB_NAME = os.getenv("POSTGRES_DB", "supply_chain_telemetry")

# 2. Database connection parameters
DB_HOST = "database"
DB_PORT = "5432"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_db_connection():
    # Returns a connetion string for the db
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

# Redis connecection
redis_client = redis.Redis(
    host="cache",
    port=6379,
    decode_responses=True
)