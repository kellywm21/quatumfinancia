from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.payment import CardCreate, CardFund, CardResponse
from src.models.payment import Card, Cardholder
from src.services.lithic_service import lithic_client
from src.services.auth_service import get_current_active_user
from src.models.payment import User

router = APIRouter(prefix="/api/cards", tags=["cards"])

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

@router.get("/{card_token}", response_model=CardResponse)
def get_card(card_token: str, db: Session = Depends(get_db)):
    """Get card details"""
    card = db.query(Card).filter(Card.card_token == card_token).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@router.get("/")
def list_cards(account_token: str = None, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """List all cards, optionally filtered by account"""
    query = db.query(Card)
    if account_token:
        query = query.filter(Card.account_token == account_token)
    
    cards = query.offset(skip).limit(limit).all()
    return cards

@router.post("/fund")
def fund_card(fund: CardFund, db: Session = Depends(get_db)):
    """Fund a card with balance"""
    try:
        # Get card from database
        card = db.query(Card).filter(Card.card_token == fund.card_token).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        if not card.financial_account_token:
            raise HTTPException(status_code=400, detail="Card financial account not configured")
        
        # Fund the card via Lithic API
        lithic_response = lithic_client.fund_card(
            financial_account_token=card.financial_account_token,
            amount=int(fund.amount),
            memo=fund.memo
        )
        
        return {
            "card_token": fund.card_token,
            "amount_funded": fund.amount,
            "status": lithic_response["status"],
            "memo": fund.memo
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{card_token}/balance")
def get_card_balance(card_token: str, db: Session = Depends(get_db)):
    """Get card balance"""
    try:
        card = db.query(Card).filter(Card.card_token == card_token).first()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        if not card.financial_account_token:
            raise HTTPException(status_code=400, detail="Card financial account not configured")
        
        balance = lithic_client.get_financial_account(card.financial_account_token)
        return balance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
