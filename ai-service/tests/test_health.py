from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ai_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "AI Microservice" in data["message"]


def test_ai_health():
    response = client.get("/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-microservice"
    assert "provider" in data
    assert "model" in data
    assert isinstance(data["api_key_configured"], bool)
    assert "GEMINI_API_KEY" not in str(data)
