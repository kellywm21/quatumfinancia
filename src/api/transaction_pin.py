from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.payment import User, TransactionPin
from src.schemas.payment import TransactionPinCreate, TransactionPinVerify, TransactionPinResponse
from src.services.auth_service import get_current_active_user, get_password_hash, verify_password

router = APIRouter(prefix="/api/transaction-pin", tags=["transaction-pin"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

@router.post("/set", response_model=TransactionPinResponse)
def set_transaction_pin(
    pin_data: TransactionPinCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set transaction PIN for user"""
    
    # Check if user already has a PIN
    existing_pin = db.query(TransactionPin).filter(
        TransactionPin.user_id == current_user.id
    ).first()
    
    if existing_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction PIN already set"
        )
    
    # Hash the PIN (reuse password hashing for consistency)
    pin_hash = get_password_hash(pin_data.pin)
    
    transaction_pin = TransactionPin(
        user_id=current_user.id,
        pin_hash=pin_hash,
        failed_attempts=0
    )
    
    db.add(transaction_pin)
    db.commit()
    db.refresh(transaction_pin)
    
    return transaction_pin

@router.post("/verify")
def verify_transaction_pin(
    pin_data: TransactionPinVerify,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Verify transaction PIN"""
    
    transaction_pin = db.query(TransactionPin).filter(
        TransactionPin.user_id == current_user.id
    ).first()
    
    if not transaction_pin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction PIN not set"
        )
    
    # Check if account is locked
    if transaction_pin.locked_until and transaction_pin.locked_until > datetime.utcnow():
        remaining_time = (transaction_pin.locked_until - datetime.utcnow()).total_seconds() / 60
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked. Try again in {int(remaining_time)} minutes"
        )
    
    # Verify PIN
    if not verify_password(pin_data.pin, transaction_pin.pin_hash):
        # Increment failed attempts
        transaction_pin.failed_attempts += 1
        
        if transaction_pin.failed_attempts >= MAX_FAILED_ATTEMPTS:
            # Lock account
            transaction_pin.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            db.add(transaction_pin)
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Too many failed attempts. Account locked for {LOCKOUT_DURATION_MINUTES} minutes"
            )
        
        db.add(transaction_pin)
        db.commit()
        
        remaining_attempts = MAX_FAILED_ATTEMPTS - transaction_pin.failed_attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid PIN. {remaining_attempts} attempts remaining"
        )
    
    # Success - reset failed attempts
    transaction_pin.failed_attempts = 0
    transaction_pin.locked_until = None
    db.add(transaction_pin)
    db.commit()
    
    return {"message": "PIN verified successfully"}

@router.put("/change", response_model=TransactionPinResponse)
def change_transaction_pin(
    pin_data: TransactionPinCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change transaction PIN"""
    
    transaction_pin = db.query(TransactionPin).filter(
        TransactionPin.user_id == current_user.id
    ).first()
    
    if not transaction_pin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction PIN not set"
        )
    
    # Hash the new PIN
    pin_hash = get_password_hash(pin_data.pin)
    
    transaction_pin.pin_hash = pin_hash
    transaction_pin.failed_attempts = 0
    transaction_pin.locked_until = None
    transaction_pin.updated_at = datetime.utcnow()
    
    db.add(transaction_pin)
    db.commit()
    db.refresh(transaction_pin)
    
    return transaction_pin

@router.get("/status", response_model=TransactionPinResponse)
def get_pin_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transaction PIN status"""
    
    transaction_pin = db.query(TransactionPin).filter(
        TransactionPin.user_id == current_user.id
    ).first()
    
    if not transaction_pin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction PIN not set"
        )
    
    return transaction_pin
