from fastapi.testclient import TestClient


def test_health_returns_fixed_contract() -> None:
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-soc-copilot",
        "version": "0.1.0",
        "environment": "local-training",
    }
