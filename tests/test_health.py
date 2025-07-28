"""
Unit test for the /health endpoint of the FastAPI application.
Ensures the endpoint returns a 200 OK and includes the expected keys.
"""
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test that the /health endpoint returns status 200 and expected JSON structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # Ensure required keys are present
    assert "status" in data
    assert "timestamp" in data
    assert "database" in data
    assert "version" in data
