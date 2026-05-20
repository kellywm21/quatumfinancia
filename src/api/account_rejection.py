from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.payment import User, AccountRejection
from src.schemas.payment import AccountRejectionResponse, AccountRejectionCreate
from src.services.auth_service import get_current_user, get_current_active_user, get_current_admin_user
from src.services.email_service import send_email
from src.services.notification_service import emit_event_notification

router = APIRouter(prefix="/api/account-rejection", tags=["account-rejection"])

@router.post("/reject", response_model=AccountRejectionResponse)
def reject_account(
    request: AccountRejectionCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reject a user account (admin only)"""
    
    # Get the user to reject
    user_to_reject = db.query(User).filter(User.id == request.user_id).first()
    if not user_to_reject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already rejected
    existing = db.query(AccountRejection).filter(
        AccountRejection.user_id == request.user_id,
        AccountRejection.status == "active"
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account already rejected"
        )
    
    # Create rejection record
    appeal_deadline = datetime.utcnow() + timedelta(days=30) if request.can_appeal else None
    
    rejection = AccountRejection(
        user_id=request.user_id,
        rejection_reason=request.rejection_reason,
        rejection_details=request.rejection_details,
        rejected_by=current_user.id,
        can_appeal=request.can_appeal,
        appeal_deadline=appeal_deadline
    )
    
    # Mark user as inactive
    user_to_reject.is_active = False
    user_to_reject.kyc_status = "rejected"
    
    db.add(rejection)
    db.add(user_to_reject)
    db.commit()
    db.refresh(rejection)
    
    emit_event_notification(
        db,
        user_id=request.user_id,
        event_type="account_rejected",
        title="Account Application Rejected",
        message=f"Your account application was rejected. Reason: {request.rejection_reason}",
        data={
            "rejection_reason": request.rejection_reason,
            "rejection_details": request.rejection_details,
            "can_appeal": request.can_appeal,
            "appeal_deadline": appeal_deadline.isoformat() if appeal_deadline else None
        }
    )
    
    return rejection

@router.get("/rejections/{user_id}", response_model=AccountRejectionResponse)
def get_account_rejection(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get rejection details for a user"""
    rejection = db.query(AccountRejection).filter(
        AccountRejection.user_id == user_id
    ).order_by(AccountRejection.created_at.desc()).first()
    
    if not rejection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rejection found for this user"
        )
    if not current_user.is_admin and rejection.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this rejection")
    return rejection

@router.post("/appeal/{rejection_id}")
def appeal_rejection(
    rejection_id: int,
    appeal_message: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Appeal an account rejection"""
    
    rejection = db.query(AccountRejection).filter(
        AccountRejection.id == rejection_id,
        AccountRejection.user_id == current_user.id
    ).first()
    
    if not rejection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rejection record not found"
        )
    
    if not rejection.can_appeal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This rejection cannot be appealed"
        )
    
    if rejection.appeal_deadline and rejection.appeal_deadline < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appeal deadline has passed"
        )
    
    if rejection.status == "appealed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appeal already submitted"
        )
    
    # Update rejection status
    rejection.status = "appealed"
    
    db.add(rejection)
    db.commit()
    
    # Send appeal notification to admins
    admin_users = db.query(User).filter(User.is_admin == True).all()
    
    for admin in admin_users:
        send_email(
            to_email=admin.email,
            subject=f"Account Appeal - User {current_user.username}",
            template="appeal_notification",
            data={
                "user_email": current_user.email,
                "user_name": current_user.full_name or current_user.username,
                "original_reason": rejection.rejection_reason,
                "appeal_message": appeal_message,
                "admin_dashboard_url": "https://app.advanciapayroll.com/admin"
            }
        )

    emit_event_notification(
        db,
        user_id=current_user.id,
        event_type="account_appeal_submitted",
        title="Appeal Submitted",
        message="Your rejection appeal has been submitted and is under review.",
        data={
            "rejection_id": rejection.id,
            "appeal_message": appeal_message
        }
    )
    
    return {
        "message": "Appeal submitted successfully",
        "status": "under_review",
        "submitted_at": datetime.utcnow().isoformat()
    }

@router.get("/pending-appeals")
def get_pending_appeals(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all pending appeals (admin only)"""
    
    appeals = db.query(AccountRejection).filter(
        AccountRejection.status == "appealed"
    ).all()
    
    result = []
    for a in appeals:
        user = db.query(User).filter(User.id == a.user_id).first()
        result.append({
            "id": a.id,
            "user_id": a.user_id,
            "username": user.username if user else None,
            "original_reason": a.rejection_reason,
            "original_details": a.rejection_details,
            "appealed_at": a.updated_at.isoformat()
        })
    return result

@router.post("/resolve-appeal/{rejection_id}")
def resolve_appeal(
    rejection_id: int,
    approved: bool,
    admin_notes: str = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Resolve an account appeal (admin only)"""
    
    rejection = db.query(AccountRejection).filter(
        AccountRejection.id == rejection_id
    ).first()
    
    if not rejection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rejection record not found"
        )
    
    if rejection.status != "appealed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This rejection is not under appeal"
        )
    
    # Get the user
    user = db.query(User).filter(User.id == rejection.user_id).first()
    
    if approved:
        # Reactivate account
        rejection.status = "resolved"
        user.is_active = True
        user.kyc_status = "pending"  # Reset to pending for re-review
        
        send_email(
            to_email=user.email,
            subject="Account Application Appeal Approved",
            template="appeal_approved",
            data={
                "user_name": user.full_name or user.username,
                "admin_notes": admin_notes
            }
        )
    else:
        # Keep rejection
        rejection.status = "resolved"
        
        send_email(
            to_email=user.email,
            subject="Account Application Appeal Denied",
            template="appeal_denied",
            data={
                "user_name": user.full_name or user.username,
                "admin_notes": admin_notes,
                "support_email": "support@advanciapayroll.com"
            }
        )
    
    db.add(rejection)
    db.add(user)
    db.commit()
    
    return {
        "message": "Appeal resolved",
        "approved": approved,
        "resolved_at": datetime.utcnow().isoformat()
    }
