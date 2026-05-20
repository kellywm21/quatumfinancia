import qrcode
import base64
from io import BytesIO
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.payment import User, DepositAddress, PendingApproval
from src.schemas.payment import DepositAddressCreate, DepositAddressResponse, PendingApprovalResponse
from src.services.auth_service import get_current_active_user
import secrets

router = APIRouter(prefix="/api/deposits", tags=["deposits"])

@router.post("/address", response_model=DepositAddressResponse)
def create_deposit_address(
    address_request: DepositAddressCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create or get deposit address for user"""
    currency = address_request.currency or "BTC"
    
    # Check if user already has an address for this currency
    existing_address = db.query(DepositAddress).filter(
        (DepositAddress.user_id == current_user.id) &
        (DepositAddress.currency == currency) &
        (DepositAddress.is_active == True)
    ).first()
    
    if existing_address:
        return existing_address
    
    # Generate a new address (in real implementation, this would call a crypto wallet service)
    # For demo purposes, we'll generate a mock address
    address = f"bc1q{secrets.token_hex(20)}" if currency == "BTC" else f"0x{secrets.token_hex(20)}"
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(address)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_code_data = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    
    # Create deposit address record
    deposit_address = DepositAddress(
        user_id=current_user.id,
        currency=currency,
        address=address,
        qr_code_data=qr_code_data,
        is_active=True
    )
    
    db.add(deposit_address)
    db.commit()
    db.refresh(deposit_address)
    
    return deposit_address

@router.get("/address", response_model=DepositAddressResponse)
def get_deposit_address(
    currency: str = "BTC",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's deposit address"""
    
    address = db.query(DepositAddress).filter(
        (DepositAddress.user_id == current_user.id) &
        (DepositAddress.currency == currency) &
        (DepositAddress.is_active == True)
    ).first()
    
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deposit address found. Please create one first."
        )
    
    return address

@router.get("/pending", response_model=list[PendingApprovalResponse])
def get_pending_approvals(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's pending approvals with ETA"""
    
    pending = db.query(PendingApproval).filter(
        (PendingApproval.user_id == current_user.id) &
        (PendingApproval.status == "pending") &
        (PendingApproval.expires_at > datetime.utcnow())
    ).order_by(PendingApproval.created_at.desc()).all()
    
    return pending
