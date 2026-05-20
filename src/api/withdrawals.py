from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.payment import User, Withdrawal, UserQueue, TransactionPin, WithdrawalApprovalTier
from src.schemas.payment import WithdrawalCreate, WithdrawalResponse
from src.services.auth_service import get_current_active_user, verify_password
from src.services.email_service import email_service
from src.services.notification_service import emit_event_notification

router = APIRouter(prefix="/api/withdrawals", tags=["withdrawals"])

AUTO_APPROVE_WITHDRAWAL_AMOUNT = 500.00


def _get_withdrawal_tier(amount: float, db: Session):
    return db.query(WithdrawalApprovalTier).filter(
        WithdrawalApprovalTier.is_active == True,
        WithdrawalApprovalTier.min_amount <= amount,
        or_(WithdrawalApprovalTier.max_amount == None, WithdrawalApprovalTier.max_amount >= amount)
    ).order_by(WithdrawalApprovalTier.min_amount.desc()).first()


@router.post("/", response_model=WithdrawalResponse)
def request_withdrawal(
    withdrawal: WithdrawalCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Request a withdrawal"""

    # Check KYC status
    if current_user.kyc_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC verification required before withdrawal"
        )

    tier = _get_withdrawal_tier(withdrawal.amount, db)

    # If the withdrawal tier requires a PIN, validate the user's PIN
    pin_record = db.query(TransactionPin).filter(TransactionPin.user_id == current_user.id).first()
    if tier and tier.requires_pin:
        if not pin_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction PIN is required for this withdrawal tier"
            )
        if not withdrawal.transaction_pin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction PIN is required for withdrawals"
            )
        if not verify_password(withdrawal.transaction_pin, pin_record.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid transaction PIN"
            )
    elif pin_record and withdrawal.transaction_pin:
        if not verify_password(withdrawal.transaction_pin, pin_record.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid transaction PIN"
            )

    approved_status = "pending"
    approved_at = None
    completed_at = None
    needs_admin_review = True

    if tier:
        if tier.auto_approve:
            approved_status = "approved"
            approved_at = datetime.utcnow()
            completed_at = datetime.utcnow()
            needs_admin_review = False
    else:
        if withdrawal.amount <= AUTO_APPROVE_WITHDRAWAL_AMOUNT:
            approved_status = "approved"
            approved_at = datetime.utcnow()
            completed_at = datetime.utcnow()
            needs_admin_review = False

    db_withdrawal = Withdrawal(
        user_id=current_user.id,
        amount=withdrawal.amount,
        currency=withdrawal.currency,
        bank_account=withdrawal.bank_account,
        memo=withdrawal.memo,
        status=approved_status,
        requested_at=datetime.utcnow(),
        approved_at=approved_at,
        completed_at=completed_at
    )

    db.add(db_withdrawal)

    if needs_admin_review:
        queue_item = UserQueue(
            user_id=current_user.id,
            status="pending",
            request_type="withdrawal",
            queue_priority=1
        )
        db.add(queue_item)

    db.commit()
    db.refresh(db_withdrawal)

    if needs_admin_review:
        emit_event_notification(
            db,
            user_id=current_user.id,
            event_type="withdrawal_pending",
            title="Withdrawal Pending Approval",
            message=f"Your withdrawal request for ${withdrawal.amount:.2f} is pending admin approval.",
            data={
                "amount": withdrawal.amount,
                "currency": withdrawal.currency,
                "bank_account": withdrawal.bank_account[-4:] if len(withdrawal.bank_account) >= 4 else withdrawal.bank_account,
                "withdrawal_id": db_withdrawal.id
            }
        )
    else:
        emit_event_notification(
            db,
            user_id=current_user.id,
            event_type="withdrawal_completed",
            title="Withdrawal Completed",
            message=f"Your withdrawal of ${withdrawal.amount:.2f} has been completed.",
            data={
                "amount": withdrawal.amount,
                "currency": withdrawal.currency,
                "bank_account": withdrawal.bank_account[-4:] if len(withdrawal.bank_account) >= 4 else withdrawal.bank_account,
                "withdrawal_id": db_withdrawal.id
            }
        )

    return db_withdrawal

@router.get("/", response_model=list[WithdrawalResponse])
def list_withdrawals(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's withdrawal requests"""
    withdrawals = db.query(Withdrawal).filter(
        Withdrawal.user_id == current_user.id
    ).offset(skip).limit(limit).all()

    return withdrawals

@router.get("/{withdrawal_id}", response_model=WithdrawalResponse)
def get_withdrawal(
    withdrawal_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get withdrawal details"""
    withdrawal = db.query(Withdrawal).filter(
        (Withdrawal.id == withdrawal_id) & (Withdrawal.user_id == current_user.id)
    ).first()

    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Withdrawal not found"
        )

    return withdrawal
