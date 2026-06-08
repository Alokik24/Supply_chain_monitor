# tests/test_health.py

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint_integration():
    """
    Integration Test: Queries the /health endpoint and verifies that 
    both Redis and PostgreSQL backing infrastructure report as Connected.
    """
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    
    # Check API status
    assert payload["api_status"] == "Live-Reload Activated" or payload["api_status"] == "Active"
    
    # Check Redis connection status
    assert payload["redis_cache"] == "Connected", "Redis Cache layer is reporting as Disconnected"
    
    # Check Postgres connection status
    assert payload["postgres_db"] == "Connected", "PostgreSQL database layer is reporting as Disconnected"