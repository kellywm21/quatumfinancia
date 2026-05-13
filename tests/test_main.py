from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_payment():
    payment_data = {
        "amount": 100.0,
        "currency": "USD",
        "description": "Test payment"
    }
    response = client.post("/api/payments/", json=payment_data)
    assert response.status_code == 200
    assert response.json()["amount"] == 100.0
    assert response.json()["status"] == "pending"

def test_list_payments():
    response = client.get("/api/payments/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
