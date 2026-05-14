import pytest
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
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    register_data = {
        "email": f"testuser{unique_id}@example.com",
        "username": f"testuser{unique_id}",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }
    register_response = client.post("/auth/register", json=register_data)
    assert register_response.status_code == 200

    login_data = {
        "username": f"testuser{unique_id}",
        "password": "TestPassword123!"
    }
    token_response = client.post("/auth/login", data=login_data)
    assert token_response.status_code == 200
    access_token = token_response.json()["access_token"]

    payment_data = {
        "amount": 100.0,
        "currency": "USD",
        "description": "Test payment"
    }
    response = client.post(
        "/api/payments/",
        json=payment_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["amount"] == 100.0
    assert response.json()["status"] == "pending"

def test_list_payments():
    response = client.get("/api/payments/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
