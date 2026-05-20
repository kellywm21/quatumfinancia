import os
import pytest
from fastapi.testclient import TestClient

# Use a temporary SQLite database for tests to avoid schema drift
test_db_path = "./test_payments.db"
if os.path.exists(test_db_path):
    os.remove(test_db_path)
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
os.environ["EMAIL_TEST_MODE"] = "true"

from src.main import app
from src.database import get_db, Base, engine, SessionLocal
from src.models.payment import Notification, User, UserQueue, Cardholder, Card
from sqlalchemy.orm import Session

# Ensure the test database schema is created fresh for each run
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def override_get_db():
    """Override database for tests"""
    from src.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

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
    from datetime import datetime, timedelta
    unique_id = str(uuid.uuid4())[:8]
    
    db = SessionLocal()
    
    # Create user directly in database to skip email verification
    from src.services.auth_service import get_password_hash
    
    user = User(
        email=f"testuser{unique_id}@example.com",
        username=f"testuser{unique_id}",
        hashed_password=get_password_hash("TestPassword123!"),
        full_name="Test User",
        email_verified=True,
        kyc_status="approved",
        kyc_approved_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    
    # Login
    login_data = {
        "username": f"testuser{unique_id}",
        "password": "TestPassword123!"
    }
    token_response = client.post("/auth/login", data=login_data)
    assert token_response.status_code == 200
    access_token = token_response.json()["access_token"]

    # Create payment
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
    db = SessionLocal()
    user = create_test_user(
        db,
        username="paymentuser",
        email="paymentuser@example.com",
        password="PaymentPass123!",
        is_admin=False,
        is_active=True
    )
    db.close()

    token = login_user("paymentuser", "PaymentPass123!")
    response = client.get(
        "/api/payments/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_card_freeze_ownership_protection():
    db = SessionLocal()
    owner_user = create_test_user(
        db,
        username="cardowner",
        email="cardowner@example.com",
        password="OwnerPass123!",
        is_admin=False,
        is_active=True
    )
    attacker_user = create_test_user(
        db,
        username="attacker",
        email="attacker@example.com",
        password="AttackPass123!",
        is_admin=False,
        is_active=True
    )

    cardholder = Cardholder(
        account_token="acct_test_123",
        email=owner_user.email,
        business_name="Owner Business",
        status="active"
    )
    db.add(cardholder)
    db.commit()
    db.refresh(cardholder)

    card = Card(
        card_token="card_test_123",
        account_token=cardholder.account_token,
        status="active"
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    db.close()

    token = login_user("attacker", "AttackPass123!")
    response = client.post(
        f"/api/cards/{card.card_token}/freeze",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def create_test_user(db, username, email, password, is_admin=False, is_active=True):
    from src.services.auth_service import get_password_hash
    user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash(password),
        full_name="Test User",
        is_admin=is_admin,
        email_verified=True,
        is_active=is_active,
        kyc_status="approved",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(username, password):
    response = client.post("/auth/login", data={
        "username": username,
        "password": password
    })
    assert response.status_code == 200
    return response.json()["access_token"]


def test_account_rejection_and_appeal_flow():
    db = SessionLocal()

    normal_user = create_test_user(
        db,
        username="normaluser",
        email="normaluser@example.com",
        password="NormalPass123!",
        is_admin=False,
        is_active=True
    )
    normal_user_id = normal_user.id

    admin_user = create_test_user(
        db,
        username="adminuser",
        email="adminuser@example.com",
        password="AdminPass123!",
        is_admin=True,
        is_active=True
    )

    db.close()

    admin_token = login_user("adminuser", "AdminPass123!")
    user_token = login_user("normaluser", "NormalPass123!")

    reject_payload = {
        "user_id": normal_user_id,
        "rejection_reason": "Invalid documents",
        "rejection_details": "Document mismatch",
        "can_appeal": True
    }

    reject_response = client.post(
        "/api/account-rejection/reject",
        json=reject_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert reject_response.status_code == 200
    rejected = reject_response.json()
    assert rejected["user_id"] == normal_user_id
    assert rejected["rejection_reason"] == "Invalid documents"
    assert rejected["status"] == "active"

    appeal_response = client.post(
        f"/api/account-rejection/appeal/{rejected['id']}",
        params={"appeal_message": "Please reconsider"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert appeal_response.status_code == 200
    assert appeal_response.json()["status"] == "under_review"

    pending_appeals_response = client.get(
        "/api/account-rejection/pending-appeals",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert pending_appeals_response.status_code == 200
    pending_appeals = pending_appeals_response.json()
    assert isinstance(pending_appeals, list)
    assert len(pending_appeals) == 1
    assert pending_appeals[0]["username"] == "normaluser"

    resolve_response = client.post(
        f"/api/account-rejection/resolve-appeal/{rejected['id']}",
        params={"approved": False, "admin_notes": "Insufficient evidence"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["approved"] is False

    pending_appeals_after = client.get(
        "/api/account-rejection/pending-appeals",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert pending_appeals_after.status_code == 200
    assert pending_appeals_after.json() == []


def test_withdrawal_tiers_and_pin_gate():
    import uuid
    from datetime import datetime

    unique_id = str(uuid.uuid4())[:8]
    db = SessionLocal()

    tier_admin_username = f"tieradmin{unique_id}"
    tier_user_username = f"tieruser{unique_id}"

    tier_admin = create_test_user(
        db,
        username=tier_admin_username,
        email=f"tieradmin{unique_id}@example.com",
        password="AdminPass123!",
        is_admin=True,
        is_active=True
    )
    tier_user = create_test_user(
        db,
        username=tier_user_username,
        email=f"tieruser{unique_id}@example.com",
        password="UserPass123!",
        is_admin=False,
        is_active=True
    )
    db.close()

    admin_token = login_user(tier_admin_username, "AdminPass123!")
    user_token = login_user(tier_user_username, "UserPass123!")

    instant_tier = client.post(
        "/api/withdrawal-tiers/tiers",
        json={
            "tier_name": f"instant-{unique_id}",
            "min_amount": 0.0,
            "max_amount": 100.0,
            "auto_approve": True,
            "processing_time_hours": 1,
            "requires_pin": False,
            "description": "Instant low-value withdrawals"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert instant_tier.status_code == 200

    secure_tier = client.post(
        "/api/withdrawal-tiers/tiers",
        json={
            "tier_name": f"secure-{unique_id}",
            "min_amount": 100.01,
            "max_amount": 1000.0,
            "auto_approve": False,
            "processing_time_hours": 24,
            "requires_pin": True,
            "description": "Medium withdrawals require PIN and review"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert secure_tier.status_code == 200

    determine_response = client.get(
        "/api/withdrawal-tiers/determine-tier",
        params={"amount": 50.0, "currency": "USD"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert determine_response.status_code == 200
    tier_data = determine_response.json()
    assert tier_data["tier_name"].startswith("instant-")
    assert tier_data["auto_approve"] is True
    assert tier_data["requires_pin"] is False

    approved_response = client.post(
        "/api/withdrawals/",
        json={
            "amount": 50.0,
            "currency": "USD",
            "bank_account": "123456789",
            "memo": "Small withdrawal"
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert approved_response.status_code == 200
    assert approved_response.json()["status"] == "approved"

    no_pin_response = client.post(
        "/api/withdrawals/",
        json={
            "amount": 150.0,
            "currency": "USD",
            "bank_account": "123456789",
            "memo": "Medium withdrawal"
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert no_pin_response.status_code == 400
    assert "PIN is required" in no_pin_response.json()["detail"]

    set_pin_response = client.post(
        "/api/transaction-pin/set",
        json={"pin": "4321"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert set_pin_response.status_code == 200

    pending_response = client.post(
        "/api/withdrawals/",
        json={
            "amount": 150.0,
            "currency": "USD",
            "bank_account": "123456789",
            "memo": "Medium withdrawal",
            "transaction_pin": "4321"
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert pending_response.status_code == 200
    assert pending_response.json()["status"] == "pending"


def test_transaction_history_endpoint():
    import uuid
    from src.models.payment import TransactionHistory

    unique_id = str(uuid.uuid4())[:8]
    db = SessionLocal()

    history_user = create_test_user(
        db,
        username=f"historyuser{unique_id}",
        email=f"historyuser{unique_id}@example.com",
        password="HistoryPass123!",
        is_admin=False,
        is_active=True
    )

    transaction = TransactionHistory(
        user_id=history_user.id,
        wallet_id=None,
        tx_type="deposit",
        amount=25.0,
        currency="USDC",
        status="confirmed",
        blockchain_hash="txhistoryhash123",
        block_explorer_url="https://etherscan.io/tx/txhistoryhash123",
        from_address="external_wallet",
        to_address="user_wallet",
        fee=0.05,
        description="History test transaction"
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    db.close()

    token = login_user(f"historyuser{unique_id}", "HistoryPass123!")

    response = client.get(
        "/api/transaction-history/user",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["id"] == transaction.id for item in data)
    assert any(item["block_explorer_url"] == "https://etherscan.io/tx/txhistoryhash123" for item in data)


def test_card_management_my_cards_and_pin():
    import uuid
    from src.models.payment import Card, Cardholder, TransactionHistory

    unique_id = str(uuid.uuid4())[:8]
    db = SessionLocal()

    card_user = create_test_user(
        db,
        username=f"carduser{unique_id}",
        email=f"carduser{unique_id}@example.com",
        password="CardPass123!",
        is_admin=False,
        is_active=True
    )

    cardholder = Cardholder(
        account_token=f"acct_{unique_id}",
        email=card_user.email,
        business_name="Card User"
    )
    db.add(cardholder)
    db.commit()
    db.refresh(cardholder)

    card = Card(
        card_token=f"card_{unique_id}",
        account_token=cardholder.account_token,
        financial_account_token=f"fin_{unique_id}",
        pan="1234",
        exp_month=12,
        exp_year=2030,
        card_type="VIRTUAL",
        status="active"
    )
    db.add(card)

    tx = TransactionHistory(
        user_id=card_user.id,
        wallet_id=None,
        tx_type="card_transaction",
        amount=50.0,
        currency="USD",
        status="completed",
        description="Test card purchase",
        tx_metadata=f'{{"card_token": "{card.card_token}"}}'
    )
    db.add(tx)
    db.commit()
    db.refresh(card)
    db.close()

    token = login_user(f"carduser{unique_id}", "CardPass123!")

    cards_response = client.get(
        "/api/cards/my-cards",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert cards_response.status_code == 200
    cards = cards_response.json()
    assert len(cards) == 1
    assert cards[0]["card_token"] == card.card_token
    assert cards[0]["pan"] == "1234"

    pin_response = client.post(
        f"/api/cards/{card.card_token}/set-pin",
        json={"pin": "1234"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert pin_response.status_code == 200
    assert pin_response.json()["message"] == "PIN set successfully"

    transactions_response = client.get(
        "/api/cards/transactions",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert transactions_response.status_code == 200
    transactions = transactions_response.json()
    assert len(transactions) == 1
    assert transactions[0]["tx_type"] == "card_transaction"
    assert transactions[0]["description"] == "Test card purchase"


def test_card_request_and_admin_approval():
    import uuid
    from src.models.payment import CardRequest, Cardholder

    unique_id = str(uuid.uuid4())[:8]
    db = SessionLocal()

    requesting_user = create_test_user(
        db,
        username=f"requser{unique_id}",
        email=f"requser{unique_id}@example.com",
        password="ReqPass123!",
        is_admin=False,
        is_active=True
    )
    requesting_user_id = requesting_user.id

    admin_user = create_test_user(
        db,
        username=f"adminreq{unique_id}",
        email=f"adminreq{unique_id}@example.com",
        password="AdminReq123!",
        is_admin=True,
        is_active=True
    )
    db.close()

    user_token = login_user(f"requser{unique_id}", "ReqPass123!")
    admin_token = login_user(f"adminreq{unique_id}", "AdminReq123!")

    # Request a card without supplying account_token
    request_response = client.post(
        "/api/cards/request",
        json={"memo": "Test card request"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert request_response.status_code == 200
    request_data = request_response.json()
    assert request_data["status"] == "pending"
    assert request_data["memo"] == "Test card request"

    # Confirm user can see pending request
    list_response = client.get(
        "/api/cards/requests",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert list_response.status_code == 200
    requests = list_response.json()
    assert any(r["id"] == request_data["id"] for r in requests)

    # Admin fetches pending card requests
    pending_response = client.get(
        "/admin/card-requests/pending",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert pending_response.status_code == 200
    pending_requests = pending_response.json()
    assert any(r["request_id"] == request_data["id"] for r in pending_requests)

    request_id = request_data["id"]
    approve_response = client.post(
        f"/admin/card-requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert approve_response.status_code == 200
    approval_data = approve_response.json()
    assert approval_data["message"] == "Card request approved"
    assert approval_data["card_token"]

    db = SessionLocal()
    notifications = db.query(Notification).filter(
        Notification.user_id == requesting_user_id,
        Notification.event_type == "card_issued"
    ).all()
    db.close()
    assert len(notifications) == 1

    # After approval, the user should now have a card
    cards_response = client.get(
        "/api/cards/my-cards",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert cards_response.status_code == 200
    cards = cards_response.json()
    assert any(c["card_token"] == approval_data["card_token"] for c in cards)


def test_admin_card_rejection_creates_notification():
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    db = SessionLocal()

    card_user = create_test_user(
        db,
        username=f"rejectuser{unique_id}",
        email=f"rejectuser{unique_id}@example.com",
        password="RejectPass123!",
        is_admin=False,
        is_active=True
    )
    card_user_id = card_user.id
    admin_user = create_test_user(
        db,
        username=f"rejectadmin{unique_id}",
        email=f"rejectadmin{unique_id}@example.com",
        password="AdminReject123!",
        is_admin=True,
        is_active=True
    )
    db.close()

    user_token = login_user(f"rejectuser{unique_id}", "RejectPass123!")
    admin_token = login_user(f"rejectadmin{unique_id}", "AdminReject123!")

    request_response = client.post(
        "/api/cards/request",
        json={"memo": "Reject test card request"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert request_response.status_code == 200
    request_id = request_response.json()["id"]

    reject_response = client.post(
        f"/admin/card-requests/{request_id}/reject",
        params={"rejection_reason": "Invalid eligibility"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["message"] == "Card request rejected"

    db = SessionLocal()
    notifications = db.query(Notification).filter(
        Notification.user_id == card_user_id,
        Notification.event_type == "card_rejected"
    ).all()
    db.close()
    assert len(notifications) == 1
    assert "Invalid eligibility" in notifications[0].message

    unread_count_response = client.get(
        "/api/notifications/user/unread-count",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert unread_count_response.status_code == 200
    assert unread_count_response.json()["unread_count"] == 1


def test_admin_card_freeze_and_unfreeze_notifications():
    import uuid
    from src.models.payment import Card, Cardholder

    unique_id = str(uuid.uuid4())[:8]
    db = SessionLocal()

    freeze_user = create_test_user(
        db,
        username=f"freezeuser{unique_id}",
        email=f"freezeuser{unique_id}@example.com",
        password="FreezePass123!",
        is_admin=False,
        is_active=True
    )
    freeze_user_id = freeze_user.id

    cardholder = Cardholder(
        account_token=f"acct_{unique_id}",
        email=freeze_user.email,
        business_name="Freeze User"
    )
    db.add(cardholder)
    db.commit()
    db.refresh(cardholder)

    card = Card(
        card_token=f"card_{unique_id}",
        account_token=cardholder.account_token,
        financial_account_token=f"fin_{unique_id}",
        pan="9999",
        exp_month=12,
        exp_year=2032,
        card_type="VIRTUAL",
        status="active"
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    card_token = card.card_token

    admin_user = create_test_user(
        db,
        username=f"freezeadmin{unique_id}",
        email=f"freezeadmin{unique_id}@example.com",
        password="AdminFreeze123!",
        is_admin=True,
        is_active=True
    )
    db.close()

    user_token = login_user(f"freezeuser{unique_id}", "FreezePass123!")
    admin_token = login_user(f"freezeadmin{unique_id}", "AdminFreeze123!")

    freeze_response = client.put(
        f"/admin/cards/{card_token}/freeze",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert freeze_response.status_code == 200
    assert freeze_response.json()["message"] == "Card frozen"

    unfreeze_response = client.put(
        f"/admin/cards/{card_token}/unfreeze",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert unfreeze_response.status_code == 200
    assert unfreeze_response.json()["message"] == "Card unfrozen"

    db = SessionLocal()
    frozen_notifications = db.query(Notification).filter(
        Notification.user_id == freeze_user_id,
        Notification.event_type == "card_frozen"
    ).all()
    unfrozen_notifications = db.query(Notification).filter(
        Notification.user_id == freeze_user_id,
        Notification.event_type == "card_unfrozen"
    ).all()
    db.close()

    assert len(frozen_notifications) == 1
    assert len(unfrozen_notifications) == 1

    unread_count_response = client.get(
        "/api/notifications/user/unread-count",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert unread_count_response.status_code == 200
    assert unread_count_response.json()["unread_count"] == 2


def test_admin_list_cards_and_freeze_unfreeze():
    import uuid
    from src.models.payment import Card, Cardholder

    unique_id = str(uuid.uuid4())[:8]
    db = SessionLocal()

    admin_user = create_test_user(
        db,
        username=f"admintest{unique_id}",
        email=f"admintest{unique_id}@example.com",
        password="AdminPass123!",
        is_admin=True,
        is_active=True
    )

    cardholder = Cardholder(
        account_token=f"acct_{unique_id}",
        email=f"cardmanage{unique_id}@example.com",
        business_name="Admin Card User"
    )
    db.add(cardholder)
    db.commit()
    db.refresh(cardholder)

    card = Card(
        card_token=f"card_{unique_id}",
        account_token=cardholder.account_token,
        financial_account_token=f"fin_{unique_id}",
        pan="5678",
        exp_month=11,
        exp_year=2029,
        card_type="VIRTUAL",
        status="active"
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    db.close()

    admin_token = login_user(f"admintest{unique_id}", "AdminPass123!")

    list_response = client.get(
        "/admin/cards",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert list_response.status_code == 200
    cards = list_response.json()
    assert any(c["card_token"] == card.card_token for c in cards)

    freeze_response = client.put(
        f"/admin/cards/{card.card_token}/freeze",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert freeze_response.status_code == 200
    assert freeze_response.json()["message"] == "Card frozen"

    unfreeze_response = client.put(
        f"/admin/cards/{card.card_token}/unfreeze",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert unfreeze_response.status_code == 200
    assert unfreeze_response.json()["message"] == "Card unfrozen"


def test_wallet_create_and_generate_address():
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    db = SessionLocal()

    wallet_user = create_test_user(
        db,
        username=f"walletuser{unique_id}",
        email=f"walletuser{unique_id}@example.com",
        password="WalletPass123!",
        is_admin=False,
        is_active=True
    )
    db.close()

    token = login_user(f"walletuser{unique_id}", "WalletPass123!")

    create_response = client.post(
        "/api/wallet/create",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert create_response.status_code == 200
    wallet_data = create_response.json()
    assert wallet_data["wallet_id"].startswith("wallet_")

    generate_response = client.post(
        "/api/wallet/addresses/generate?currency=BTC&label=New%20BTC%20Address",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert generate_response.status_code == 200
    address_data = generate_response.json()
    assert address_data["currency"] == "BTC"
    assert address_data["label"] == "New BTC Address"

    addresses_response = client.get(
        "/api/wallet/addresses?currency=BTC",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert addresses_response.status_code == 200
    addresses = addresses_response.json()
    assert any(addr["address"] == address_data["address"] for addr in addresses)


def test_admin_queue_filtering():
    db = SessionLocal()

    admin_user = create_test_user(
        db,
        username="queueadmin",
        email="queueadmin@example.com",
        password="AdminPass123!",
        is_admin=True,
        is_active=True
    )
    user_withdrawal = create_test_user(
        db,
        username="queuewithdrawal",
        email="queuewithdrawal@example.com",
        password="UserPass123!",
        is_admin=False,
        is_active=True
    )
    user_card = create_test_user(
        db,
        username="queuecard",
        email="queuecard@example.com",
        password="UserPass123!",
        is_admin=False,
        is_active=True
    )

    queue_withdrawal = UserQueue(
        user_id=user_withdrawal.id,
        status="pending",
        request_type="withdrawal",
        queue_priority=1
    )
    queue_card = UserQueue(
        user_id=user_card.id,
        status="pending",
        request_type="card_issue",
        queue_priority=2
    )
    db.add(queue_withdrawal)
    db.add(queue_card)
    db.commit()
    db.close()

    admin_token = login_user("queueadmin", "AdminPass123!")

    all_response = client.get(
        "/admin/queue",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert all_response.status_code == 200
    all_items = all_response.json()
    assert isinstance(all_items, list)
    assert len(all_items) >= 2

    withdrawal_response = client.get(
        "/admin/queue?request_type=withdrawal",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert withdrawal_response.status_code == 200
    withdrawal_items = withdrawal_response.json()
    assert len(withdrawal_items) >= 1
    assert all(item["request_type"] == "withdrawal" for item in withdrawal_items)

    card_response = client.get(
        "/admin/queue?request_type=card_issue",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert card_response.status_code == 200
    card_items = card_response.json()
    assert len(card_items) == 1
    assert card_items[0]["request_type"] == "card_issue"


def test_notification_trigger_setup_and_withdrawal_pending():
    db = SessionLocal()

    admin_user = create_test_user(
        db,
        username="notifadmin",
        email="notifadmin@example.com",
        password="AdminPass123!",
        is_admin=True,
        is_active=True
    )
    normal_user = create_test_user(
        db,
        username="notifuser",
        email="notifuser@example.com",
        password="UserPass123!",
        is_admin=False,
        is_active=True
    )
    db.close()

    admin_token = login_user("notifadmin", "AdminPass123!")
    user_token = login_user("notifuser", "UserPass123!")

    setup_response = client.post(
        "/api/notifications/triggers/setup",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert setup_response.status_code == 200
    assert "withdrawal_pending" in setup_response.json().get("created_triggers", [])

    pin_response = client.post(
        "/api/transaction-pin/set",
        json={"pin": "4321"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert pin_response.status_code == 200

    pending_response = client.post(
        "/api/withdrawals/",
        json={
            "amount": 150.0,
            "currency": "USD",
            "bank_account": "123456789",
            "memo": "Notification test",
            "transaction_pin": "4321"
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert pending_response.status_code == 200
    assert pending_response.json()["status"] == "pending"

    notifications_response = client.get(
        "/api/notifications/user/all",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert notifications_response.status_code == 200
    notifications = notifications_response.json()
    assert any(note["event_type"] == "withdrawal_pending" for note in notifications)


def test_notification_read_and_unread_count():
    db = SessionLocal()

    admin_user = create_test_user(
        db,
        username="notifadmin2",
        email="notifadmin2@example.com",
        password="AdminPass123!",
        is_admin=True,
        is_active=True
    )
    normal_user = create_test_user(
        db,
        username="notifuser2",
        email="notifuser2@example.com",
        password="UserPass123!",
        is_admin=False,
        is_active=True
    )
    db.close()

    admin_token = login_user("notifadmin2", "AdminPass123!")
    user_token = login_user("notifuser2", "UserPass123!")

    setup_response = client.post(
        "/api/notifications/triggers/setup",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert setup_response.status_code == 200

    emit_response = client.post(
        f"/api/notifications/emit?user_id={normal_user.id}&event_type=withdrawal_pending&title=Test+Notification&message=This+is+a+test+notification",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert emit_response.status_code == 200
    notification_data = emit_response.json()
    assert notification_data["event_type"] == "withdrawal_pending"

    count_response = client.get(
        "/api/notifications/user/unread-count",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert count_response.status_code == 200
    assert count_response.json()["unread_count"] >= 1

    all_response = client.get(
        "/api/notifications/user/all",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert all_response.status_code == 200
    notifications = all_response.json()
    assert any(note["id"] == notification_data["id"] for note in notifications)

    mark_read_response = client.post(
        f"/api/notifications/user/{notification_data['id']}/read",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert mark_read_response.status_code == 200

    count_response_after = client.get(
        "/api/notifications/user/unread-count",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert count_response_after.status_code == 200
    assert count_response_after.json()["unread_count"] == 0

    read_all_response = client.post(
        "/api/notifications/user/read-all",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert read_all_response.status_code == 200
    assert "count" in read_all_response.json()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get database URL from config
from src.config import settings
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
