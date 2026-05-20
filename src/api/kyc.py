from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import os
from pathlib import Path
from src.database import get_db
from src.models.payment import User, KYC, UserQueue
from src.schemas.payment import KYCCreate, KYCResponse
from src.services.auth_service import get_current_active_user
from src.services.email_service import email_service

router = APIRouter(prefix="/api/kyc", tags=["kyc"])

@router.post("/submit", response_model=dict)
def submit_kyc(
    kyc_data: KYCCreate,
    id_document: UploadFile = File(...),
    selfie: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit KYC verification documents"""
    
    # Check if user already has pending KYC
    existing_kyc = db.query(KYC).filter(
        (KYC.user_id == current_user.id) & (KYC.status == "pending")
    ).first()
    
    if existing_kyc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending KYC submission"
        )
    
    # Validate file types
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if id_document.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="ID document must be a JPEG or PNG image")
    if selfie.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Selfie must be a JPEG or PNG image")
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads/kyc")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save files
    id_filename = f"{current_user.id}_id_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{id_document.filename.split('.')[-1]}"
    selfie_filename = f"{current_user.id}_selfie_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{selfie.filename.split('.')[-1]}"
    
    id_path = upload_dir / id_filename
    selfie_path = upload_dir / selfie_filename
    
    with open(id_path, "wb") as f:
        f.write(id_document.file.read())
    
    with open(selfie_path, "wb") as f:
        f.write(selfie.file.read())
    
    # Create KYC record
    kyc = KYC(
        user_id=current_user.id,
        first_name=kyc_data.first_name,
        last_name=kyc_data.last_name,
        date_of_birth=kyc_data.date_of_birth,
        country=kyc_data.country,
        document_type=kyc_data.document_type,
        document_number=kyc_data.document_number,
        address=kyc_data.address,
        city=kyc_data.city,
        postal_code=kyc_data.postal_code,
        id_document_path=str(id_path),
        selfie_path=str(selfie_path),
        status="pending",
        submitted_at=datetime.utcnow()
    )
    
    # Update user KYC status
    current_user.kyc_status = "submitted"
    current_user.kyc_submitted_at = datetime.utcnow()
    
    # Add to user queue
    queue_item = UserQueue(
        user_id=current_user.id,
        status="pending",
        request_type="kyc_review",
        queue_priority=0
    )
    
    db.add(kyc)
    db.add(current_user)
    db.add(queue_item)
    db.commit()
    
    # Send notification email
    email_service.send_kyc_pending_email(current_user.email, current_user.username)
    
    return {
        "message": "KYC submitted successfully",
        "status": "pending",
        "kyc_id": kyc.id
    }

@router.get("/status", response_model=dict)
def get_kyc_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current KYC status"""
    kyc = db.query(KYC).filter(KYC.user_id == current_user.id).order_by(KYC.id.desc()).first()
    
    if not kyc:
        return {
            "status": "not_submitted",
            "message": "No KYC data submitted yet"
        }
    
    return {
        "status": kyc.status,
        "submitted_at": kyc.submitted_at,
        "verified_at": kyc.verified_at,
        "rejection_reason": kyc.rejection_reason
    }

@router.get("/my", response_model=KYCResponse)
def get_my_kyc(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's KYC data"""
    kyc = db.query(KYC).filter(KYC.user_id == current_user.id).order_by(KYC.id.desc()).first()
    
    if not kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No KYC data found"
        )
    
    return kyc
