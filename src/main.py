# src/main.py

from fastapi import FastAPI
from db import get_db_connection, redis_client

app = FastAPI()

@app.get("/")
def read_root():
    health_status = {"api_status": "Live-Reload Activated"}
    
    # Test Redis Channel Connection
    try:
        redis_client.ping()
        health_status["redis_cache"] = "Connected"
    except Exception:
        health_status["redis_cache"] = "Disconnected"
        
    # Test Postgres Database Connection
    db_conn = get_db_connection()
    if db_conn:
        health_status["postgres_db"] = "Connected"
        db_conn.close()
    else:
        health_status["postgres_db"] = "Disconnected"
        
    return health_status