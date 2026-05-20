from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.payment import (
    CardCreate, CardFund, CardResponse, CardRequestCreate,
    CardRequestResponse, CardLimitUpdate, CardPinRequest,
    TransactionHistoryResponse
)
from src.models.payment import (
    Card, Cardholder, CardRequest, UserQueue, TransactionHistory
)
from src.services.lithic_service import lithic_client
from src.services.auth_service import get_current_active_user, get_password_hash
from src.services.email_service import email_service
from src.models.payment import User

router = APIRouter(prefix="/api/cards", tags=["cards"])

def _validate_card_owner(card, current_user: User, db: Session):
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    cardholder = db.query(Cardholder).filter(Cardholder.account_token == card.account_token).first()
    if not cardholder:
        raise HTTPException(status_code=404, detail="Cardholder not found")
    if not current_user.is_admin and cardholder.email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to access this card")
    return card

@router.post("/", response_model=CardResponse)
def issue_virtual_card(
    card: CardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Issue a new virtual card via Lithic"""
    try:
        # Verify cardholder exists
        cardholder = db.query(Cardholder).filter(
            Cardholder.account_token == card.account_token
        ).first()
        
        if not cardholder:
            raise HTTPException(status_code=404, detail="Cardholder not found")
        if not current_user.is_admin and cardholder.email != current_user.email:
            raise HTTPException(status_code=403, detail="Not authorized to issue a card for this cardholder")
        
        # Create card via Lithic API
        lithic_response = lithic_client.create_card(
            account_token=card.account_token,
            card_type=card.card_type,
            spend_limit=int(card.spend_limit),
            spend_limit_duration=card.spend_limit_duration,
            memo=card.memo
        )
        
        # Save to database
        db_card = Card(
            card_token=lithic_response["card_token"],
            account_token=lithic_response["account_token"],
            financial_account_token=lithic_response["financial_account_token"],
            pan=lithic_response["pan"],
            cvv=lithic_response["cvv"],
            exp_month=lithic_response["exp_month"],
            exp_year=lithic_response["exp_year"],
            card_type=lithic_response["card_type"],
            status=lithic_response["status"],
            spend_limit=lithic_response["spend_limit"],
            spend_limit_duration=lithic_response["spend_limit_duration"],
            memo=lithic_response.get("memo")
        )
        db.add(db_card)
        db.commit()
        db.refresh(db_card)
        return db_card
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/request", response_model=CardRequestResponse)
def request_virtual_card(
    card_request: CardRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Request a new virtual card for approval"""
    account_token = card_request.account_token
    if not account_token:
        cardholder = db.query(Cardholder).filter(
            Cardholder.email == current_user.email
        ).first()
        if not cardholder:
            lithic_response = lithic_client.create_cardholder(
                email=current_user.email
            )
            cardholder = Cardholder(
                account_token=lithic_response["account_token"],
                email=lithic_response["email"],
                status=lithic_response.get("status", "active")
            )
            db.add(cardholder)
            db.commit()
            db.refresh(cardholder)
        account_token = cardholder.account_token
    else:
        cardholder = db.query(Cardholder).filter(
            Cardholder.account_token == account_token
        ).first()
        if not cardholder:
            raise HTTPException(status_code=404, detail="Cardholder not found")
        if cardholder.email != current_user.email:
            raise HTTPException(status_code=403, detail="Unauthorized cardholder")

    db_card_request = CardRequest(
        user_id=current_user.id,
        account_token=account_token,
        card_type=card_request.card_type,
        spend_limit=card_request.spend_limit,
        spend_limit_duration=card_request.spend_limit_duration,
        memo=card_request.memo,
        status="pending",
        requested_at=datetime.utcnow()
    )

    queue_item = UserQueue(
        user_id=current_user.id,
        status="pending",
        request_type="card_issue",
        queue_priority=2
    )

    db.add(db_card_request)
    db.add(queue_item)
    db.commit()
    db.refresh(db_card_request)
    return db_card_request

@router.get("/requests", response_model=list[CardRequestResponse])
def list_card_requests(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List card requests for the current user"""
    requests = db.query(CardRequest).filter(
        CardRequest.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return requests

@router.post("/{card_token}/freeze")
def freeze_card(
    card_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Freeze a card to prevent new transactions"""
    card = _validate_card_owner(db.query(Card).filter(Card.card_token == card_token).first(), current_user, db)

    card.status = "frozen"
    db.add(card)
    db.commit()
    return {"message": "Card frozen"}

@router.post("/{card_token}/unfreeze")
def unfreeze_card(
    card_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Unfreeze a previously frozen card"""
    card = _validate_card_owner(db.query(Card).filter(Card.card_token == card_token).first(), current_user, db)

    card.status = "active"
    db.add(card)
    db.commit()
    return {"message": "Card unfrozen"}

@router.patch("/{card_token}/limits")
def update_card_limits(
    card_token: str,
    limits: CardLimitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update card spend limits"""
    card = _validate_card_owner(db.query(Card).filter(Card.card_token == card_token).first(), current_user, db)

    if limits.spend_limit is not None:
        card.spend_limit = limits.spend_limit
    if limits.spend_limit_duration is not None:
        card.spend_limit_duration = limits.spend_limit_duration

    db.add(card)
    db.commit()
    return card

@router.get("/my-cards", response_model=list[CardResponse])
def get_my_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all cards for the current user"""
    cardholder = db.query(Cardholder).filter(Cardholder.email == current_user.email).first()
    if not cardholder:
        return []

    cards = db.query(Card).filter(Card.account_token == cardholder.account_token).all()
    result = []
    for card in cards:
        result.append({
            "id": card.id,
            "card_token": card.card_token,
            "account_token": card.account_token,
            "financial_account_token": card.financial_account_token,
            "pan": card.pan,
            "exp_month": card.exp_month,
            "exp_year": card.exp_year,
            "card_type": card.card_type,
            "status": card.status,
            "spend_limit": card.spend_limit,
            "spend_limit_duration": card.spend_limit_duration,
            "memo": card.memo,
            "available_balance": None,
            "last_four": card.pan,
            "created_at": card.created_at,
            "updated_at": card.updated_at
        })
    return result

@router.get("/transactions", response_model=list[TransactionHistoryResponse])
def list_card_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List card-related transactions for the current user"""
    transactions = db.query(TransactionHistory).filter(
        TransactionHistory.user_id == current_user.id,
        TransactionHistory.tx_type.in_(["card_transaction", "card_funding"])
    ).order_by(TransactionHistory.created_at.desc()).all()
    return transactions

@router.post("/{card_token}/set-pin")
def set_card_pin(
    card_token: str,
    pin_data: CardPinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Set a PIN for a card"""
    card = _validate_card_owner(db.query(Card).filter(Card.card_token == card_token).first(), current_user, db)
    if len(pin_data.pin) != 4 or not pin_data.pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be a 4-digit code")

    card.pin_hash = get_password_hash(pin_data.pin)
    db.add(card)
    db.commit()
    return {"message": "PIN set successfully"}

@router.get("/{card_token}", response_model=CardResponse)
def get_card(
    card_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get card details"""
    card = db.query(Card).filter(Card.card_token == card_token).first()
    _validate_card_owner(card, current_user, db)
    return card

@router.get("/")
def list_cards(
    account_token: str = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all cards, optionally filtered by account"""
    if current_user.is_admin:
        query = db.query(Card)
        if account_token:
            query = query.filter(Card.account_token == account_token)
    else:
        cardholder = db.query(Cardholder).filter(Cardholder.email == current_user.email).first()
        if not cardholder:
            return []
        query = db.query(Card).filter(Card.account_token == cardholder.account_token)
    cards = query.offset(skip).limit(limit).all()
    return cards

@router.post("/fund")
def fund_card(
    fund: CardFund,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Fund a card by converting crypto to USD"""
    try:
        # Get card from database and ensure the user owns it
        card = _validate_card_owner(db.query(Card).filter(Card.card_token == fund.card_token).first(), current_user, db)
        if not card.financial_account_token:
            raise HTTPException(status_code=400, detail="Card financial account not configured")

        # Get user's wallet balance (assuming USD for now, but should be crypto)
        # In a real implementation, this would check the user's crypto balance
        # For demo, we'll assume the amount is in USD cents as before

        # Convert amount to cents (assuming fund.amount is in USD)
        usd_amount_cents = int(fund.amount * 100)

        # Fund the card via Lithic API
        lithic_response = lithic_client.fund_card(
            financial_account_token=card.financial_account_token,
            amount=usd_amount_cents,
            memo=fund.memo
        )

        # Record the transaction
        from src.models.payment import TransactionHistory
        tx = TransactionHistory(
            user_id=current_user.id,
            tx_type="card_funding",
            amount=fund.amount,
            currency="USD",
            fee=0.0,
            status="completed",
            description=f"Card funding: {fund.memo}",
            tx_metadata=f'{{"card_token": "{fund.card_token}"}}'
        )
        db.add(tx)
        db.commit()

        email_service.send_card_funded_email(
            current_user.email,
            current_user.username,
            fund.amount,
            fund.card_token
        )

        return {
            "card_token": fund.card_token,
            "amount_funded_usd": fund.amount,
            "status": lithic_response["status"],
            "memo": fund.memo,
            "transaction_id": tx.id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{card_token}/balance")
def get_card_balance(
    card_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get card balance"""
    try:
        card = db.query(Card).filter(Card.card_token == card_token).first()
        _validate_card_owner(card, current_user, db)
        if not card.financial_account_token:
            raise HTTPException(status_code=400, detail="Card financial account not configured")
        balance = lithic_client.get_financial_account(card.financial_account_token)
        return balance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
