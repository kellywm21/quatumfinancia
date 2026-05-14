from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.payment import PaymentCreate, PaymentResponse
from src.models.payment import Payment
from src.services.auth_service import get_current_active_user
from src.models.payment import User
import uuid

router = APIRouter(prefix="/api/payments", tags=["payments"])

@router.post("/", response_model=PaymentResponse)
def create_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new payment"""
    transaction_id = str(uuid.uuid4())
    db_payment = Payment(
        transaction_id=transaction_id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        status="pending"
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@router.get("/{transaction_id}", response_model=PaymentResponse)
def get_payment(transaction_id: str, db: Session = Depends(get_db)):
    """Get payment details"""
    payment = db.query(Payment).filter(Payment.transaction_id == transaction_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

@router.get("/")
def list_payments(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """List all payments"""
    payments = db.query(Payment).offset(skip).limit(limit).all()
    return payments
