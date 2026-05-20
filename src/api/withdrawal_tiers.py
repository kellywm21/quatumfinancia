from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from src.database import get_db
from src.models.payment import (
    User, Withdrawal, WithdrawalApprovalTier, TransactionHistory
)
from src.schemas.payment import WithdrawalApprovalTierResponse
from src.services.auth_service import get_current_active_user, get_current_admin_user
from src.services.email_service import email_service, send_email

router = APIRouter(prefix="/api/withdrawal-tiers", tags=["withdrawal-tiers"])

@router.post("/tiers", response_model=WithdrawalApprovalTierResponse)
def create_withdrawal_tier(
    tier_data: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create withdrawal approval tier (admin only)"""
    
    existing = db.query(WithdrawalApprovalTier).filter(
        WithdrawalApprovalTier.tier_name == tier_data.get("tier_name")
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tier already exists"
        )
    
    tier = WithdrawalApprovalTier(
        tier_name=tier_data.get("tier_name"),
        min_amount=tier_data.get("min_amount", 0.0),
        max_amount=tier_data.get("max_amount"),
        auto_approve=tier_data.get("auto_approve", False),
        processing_time_hours=tier_data.get("processing_time_hours", 24),
        requires_pin=tier_data.get("requires_pin", True),
        description=tier_data.get("description")
    )
    
    db.add(tier)
    db.commit()
    db.refresh(tier)
    
    return tier

@router.get("/tiers", response_model=list[WithdrawalApprovalTierResponse])
def list_withdrawal_tiers(db: Session = Depends(get_db)):
    """Get all active withdrawal tiers"""
    
    tiers = db.query(WithdrawalApprovalTier).filter(
        WithdrawalApprovalTier.is_active == True
    ).order_by(WithdrawalApprovalTier.min_amount).all()
    
    return tiers

@router.get("/tiers/{tier_id}", response_model=WithdrawalApprovalTierResponse)
def get_withdrawal_tier(
    tier_id: int,
    db: Session = Depends(get_db)
):
    """Get withdrawal tier details"""
    
    tier = db.query(WithdrawalApprovalTier).filter(
        WithdrawalApprovalTier.id == tier_id
    ).first()
    
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tier not found"
        )
    
    return tier

@router.get("/determine-tier")
def determine_withdrawal_tier(
    amount: float,
    currency: str = "USD",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Determine which tier applies to a withdrawal amount"""
    
    tier = db.query(WithdrawalApprovalTier).filter(
        and_(
            WithdrawalApprovalTier.min_amount <= amount,
            WithdrawalApprovalTier.is_active == True,
            or_(
                WithdrawalApprovalTier.max_amount == None,
                WithdrawalApprovalTier.max_amount >= amount
            )
        )
    ).order_by(WithdrawalApprovalTier.min_amount.desc()).first()
    
    if tier and tier.max_amount and amount > tier.max_amount:
        # Find next tier if this exceeds max
        tier = None
    
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No approval tier available for amount: {amount} {currency}"
        )
    
    return {
        "tier_id": tier.id,
        "tier_name": tier.tier_name,
        "auto_approve": tier.auto_approve,
        "processing_time_hours": tier.processing_time_hours,
        "requires_pin": tier.requires_pin,
        "requires_admin_review": not tier.auto_approve
    }

@router.post("/request-with-tier")
def request_withdrawal_with_tier(
    amount: float,
    bank_account: str,
    currency: str = "USD",
    memo: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Request withdrawal using automatic tier determination"""
    
    # Determine tier
    tier = db.query(WithdrawalApprovalTier).filter(
        and_(
            WithdrawalApprovalTier.min_amount <= amount,
            WithdrawalApprovalTier.is_active == True,
            or_(
                WithdrawalApprovalTier.max_amount == None,
                WithdrawalApprovalTier.max_amount >= amount
            )
        )
    ).order_by(WithdrawalApprovalTier.min_amount.desc()).first()
    
    if not tier or (tier.max_amount and amount > tier.max_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No approval tier available for amount: {amount} {currency}"
        )
    
    # Create withdrawal
    withdrawal = Withdrawal(
        user_id=current_user.id,
        amount=amount,
        currency=currency,
        bank_account=bank_account,
        memo=memo,
        status="auto_approved" if tier.auto_approve else "pending"
    )
    
    if tier.auto_approve:
        withdrawal.approved_at = datetime.utcnow()
        withdrawal.status = "completed"
        withdrawal.completed_at = datetime.utcnow()
    
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)
    
    # Create transaction history
    tx_history = TransactionHistory(
        user_id=current_user.id,
        tx_type="withdrawal",
        amount=amount,
        currency=currency,
        status=withdrawal.status,
        from_address=None,
        to_address=bank_account,
        description=memo or f"Withdrawal via tier: {tier.tier_name}"
    )
    
    if tier.auto_approve:
        tx_history.confirmed_at = datetime.utcnow()
        tx_history.status = "confirmed"
    
    db.add(tx_history)
    db.commit()
    
    # Send email notification
    if tier.auto_approve:
        send_email(
            to_email=current_user.email,
            subject="Withdrawal Completed",
            template="withdrawal_completed",
            data={
                "user_name": current_user.full_name or current_user.username,
                "amount": amount,
                "currency": currency,
                "bank_account": bank_account[-4:] if len(bank_account) >= 4 else "****"
            }
        )
    else:
        email_service.send_withdrawal_pending_email(
            recipient_email=current_user.email,
            amount=amount,
            currency=currency
        )

    return {
        "withdrawal_id": withdrawal.id,
        "status": withdrawal.status,
        "tier": tier.tier_name,
        "auto_approved": tier.auto_approve,
        "eta_hours": tier.processing_time_hours if not tier.auto_approve else 0
    }
