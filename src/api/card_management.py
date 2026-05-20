from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.database import get_db
from src.models.payment import User, Card, Cardholder, CardManagement, TransactionHistory
from src.schemas.payment import CardManagementResponse
from src.services.auth_service import get_current_active_user
from src.services.email_service import send_email

router = APIRouter(prefix="/api/card-management", tags=["card-management"])

@router.get("/cards", response_model=list[CardManagementResponse])
def get_user_cards(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all card management records for user"""
    
    cards = db.query(CardManagement).filter(
        CardManagement.user_id == current_user.id
    ).all()
    
    return cards

@router.get("/cards/{card_id}", response_model=CardManagementResponse)
def get_card_management(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get card management details"""
    
    card_mgmt = db.query(CardManagement).filter(
        and_(
            CardManagement.card_id == card_id,
            CardManagement.user_id == current_user.id
        )
    ).first()
    
    if not card_mgmt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card management record not found"
        )
    
    return card_mgmt

@router.post("/freeze")
def freeze_card(
    card_id: str,
    reason: str = "manual",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Freeze a card to prevent transactions"""
    
    # Verify card exists and belongs to user
    card = db.query(Card).filter(Card.card_token == card_id).first()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    card_mgmt = db.query(CardManagement).filter(
        and_(
            CardManagement.card_id == card_id,
            CardManagement.user_id == current_user.id
        )
    ).first()
    
    if not card_mgmt:
        card_mgmt = CardManagement(
            card_id=card_id,
            user_id=current_user.id,
            is_frozen=True,
            freeze_reason=reason,
            frozen_at=datetime.utcnow()
        )
    else:
        if card_mgmt.is_frozen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Card is already frozen"
            )
        
        card_mgmt.is_frozen = True
        card_mgmt.freeze_reason = reason
        card_mgmt.frozen_at = datetime.utcnow()
    
    # Also update card status
    card.status = "frozen"
    
    db.add(card_mgmt)
    db.add(card)
    db.commit()
    db.refresh(card_mgmt)
    
    # Send notification
    send_email(
        to_email=current_user.email,
        subject="Card Frozen",
        template="card_frozen",
        data={
            "user_name": current_user.full_name or current_user.username,
            "reason": reason,
            "card_last_4": card_id[-4:]
        }
    )
    
    return {
        "message": "Card frozen successfully",
        "card_id": card_id,
        "is_frozen": True,
        "frozen_at": datetime.utcnow().isoformat()
    }

@router.post("/unfreeze")
def unfreeze_card(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unfreeze a card to allow transactions"""
    
    card_mgmt = db.query(CardManagement).filter(
        and_(
            CardManagement.card_id == card_id,
            CardManagement.user_id == current_user.id
        )
    ).first()
    
    if not card_mgmt or not card_mgmt.is_frozen:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card is not frozen"
        )
    
    card_mgmt.is_frozen = False
    card_mgmt.freeze_reason = None
    card_mgmt.frozen_at = None
    
    # Update card status
    card = db.query(Card).filter(Card.card_token == card_id).first()
    if card:
        card.status = "active"
        db.add(card)
    
    db.add(card_mgmt)
    db.commit()
    db.refresh(card_mgmt)
    
    # Send notification
    send_email(
        to_email=current_user.email,
        subject="Card Unfrozen",
        template="card_unfrozen",
        data={
            "user_name": current_user.full_name or current_user.username,
            "card_last_4": card_id[-4:]
        }
    )
    
    return {
        "message": "Card unfrozen successfully",
        "card_id": card_id,
        "is_frozen": False
    }

@router.post("/set-limit")
def set_card_limit(
    card_id: str,
    spend_limit: float,
    period: str = "monthly",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set spending limit for a card"""
    
    if spend_limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spend limit must be positive"
        )
    
    if period not in ["daily", "weekly", "monthly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Period must be daily, weekly, or monthly"
        )
    
    card_mgmt = db.query(CardManagement).filter(
        and_(
            CardManagement.card_id == card_id,
            CardManagement.user_id == current_user.id
        )
    ).first()
    
    if not card_mgmt:
        card_mgmt = CardManagement(
            card_id=card_id,
            user_id=current_user.id,
            spend_limit=spend_limit,
            spend_limit_period=period
        )
    else:
        card_mgmt.spend_limit = spend_limit
        card_mgmt.spend_limit_period = period
    
    # Also update card
    card = db.query(Card).filter(Card.card_token == card_id).first()
    if card:
        card.spend_limit = int(spend_limit * 100)  # Store in cents
        card.spend_limit_duration = period.upper()
        db.add(card)
    
    db.add(card_mgmt)
    db.commit()
    db.refresh(card_mgmt)
    
    return {
        "message": "Spending limit set successfully",
        "card_id": card_id,
        "spend_limit": spend_limit,
        "period": period
    }

@router.get("/transaction-history/{card_id}")
def get_card_transaction_history(
    card_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transaction history for a specific card"""
    
    # Verify card belongs to user
    card_mgmt = db.query(CardManagement).filter(
        and_(
            CardManagement.card_id == card_id,
            CardManagement.user_id == current_user.id
        )
    ).first()
    
    if not card_mgmt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    # Get transactions related to this card
    transactions = db.query(TransactionHistory).filter(
        and_(
            TransactionHistory.user_id == current_user.id,
            TransactionHistory.tx_type == "card_transaction",
            TransactionHistory.description.contains(card_id) |
            TransactionHistory.tx_metadata.contains(card_id)
        )
    ).order_by(TransactionHistory.created_at.desc()).limit(limit).all()
    
    # Get card management stats
    card_stats = {
        "transaction_count": card_mgmt.transaction_count,
        "total_spent": card_mgmt.total_spent,
        "last_used_at": card_mgmt.last_used_at,
        "spend_limit": card_mgmt.spend_limit,
        "spend_limit_period": card_mgmt.spend_limit_period,
        "remaining_limit": (card_mgmt.spend_limit - card_mgmt.total_spent) if card_mgmt.spend_limit else None
    }
    
    return {
        "card_stats": card_stats,
        "recent_transactions": transactions
    }

@router.post("/create-management-record")
def create_card_management_record(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a card management record for a newly issued card"""
    
    # Verify card exists and belongs to user
    card = db.query(Card).filter(Card.card_token == card_id).first()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    # Check if record already exists
    existing = db.query(CardManagement).filter(
        CardManagement.card_id == card_id
    ).first()
    
    if existing:
        if existing.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create or view this card management record"
            )
        return existing

    # Verify the card belongs to the current user
    cardholder = db.query(Cardholder).filter(Cardholder.account_token == card.account_token).first()
    if cardholder and not current_user.is_admin and cardholder.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create a management record for this card"
        )
    # Create record
    card_mgmt = CardManagement(
        card_id=card_id,
        user_id=current_user.id,
        is_frozen=False,
        transaction_count=0,
        total_spent=0.0
    )
    
    db.add(card_mgmt)
    db.commit()
    db.refresh(card_mgmt)
    
    return card_mgmt

@router.get("/limits-info/{card_id}")
def get_card_limits_info(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed limit information for a card"""
    
    card_mgmt = db.query(CardManagement).filter(
        and_(
            CardManagement.card_id == card_id,
            CardManagement.user_id == current_user.id
        )
    ).first()
    
    if not card_mgmt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    card = db.query(Card).filter(Card.card_token == card_id).first()
    
    # Calculate remaining limit
    spend_limit = card_mgmt.spend_limit or (card.spend_limit / 100 if card and card.spend_limit else None)
    total_spent = card_mgmt.total_spent
    remaining = (spend_limit - total_spent) if spend_limit else None
    
    return {
        "card_id": card_id,
        "spend_limit": spend_limit,
        "spend_limit_period": card_mgmt.spend_limit_period,
        "total_spent": total_spent,
        "remaining_limit": remaining,
        "remaining_percentage": ((remaining / spend_limit) * 100) if spend_limit else None,
        "transaction_count": card_mgmt.transaction_count,
        "is_frozen": card_mgmt.is_frozen,
        "freeze_reason": card_mgmt.freeze_reason,
        "last_used_at": card_mgmt.last_used_at
    }
