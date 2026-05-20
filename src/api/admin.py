from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.payment import User, KYC, Withdrawal, UserQueue, CardRequest, Card, Cardholder
from src.schemas.payment import WithdrawalApprove, KYCResponse
from src.services.auth_service import get_current_admin_user
from src.services.email_service import email_service
from src.services.lithic_service import lithic_client
from src.services.notification_service import emit_event_notification

router = APIRouter(prefix="/admin", tags=["admin"])

# User Queue Management

@router.get("/queue", response_model=list[dict])
def get_user_queue(
    request_type: str | None = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get pending user queue items (admin only)"""
    query = db.query(UserQueue).filter(UserQueue.status == "pending")

    if request_type:
        query = query.filter(UserQueue.request_type == request_type)

    queue_items = query.order_by(
        UserQueue.queue_priority.desc(),
        UserQueue.created_at.asc()
    ).all()
    
    result = []
    for item in queue_items:
        user = db.query(User).filter(User.id == item.user_id).first()
        result.append({
            "queue_id": item.id,
            "user_id": item.user_id,
            "username": user.username,
            "email": user.email,
            "request_type": item.request_type,
            "priority": item.queue_priority,
            "created_at": item.created_at
        })
    
    return result

@router.put("/queue/{queue_id}/mark-processing")
def mark_queue_processing(
    queue_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Mark queue item as processing (admin only)"""
    queue_item = db.query(UserQueue).filter(UserQueue.id == queue_id).first()
    
    if not queue_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found"
        )
    
    queue_item.status = "processing"
    queue_item.updated_at = datetime.utcnow()
    db.add(queue_item)
    db.commit()
    
    return {"message": "Queue item marked as processing"}

# KYC Management

@router.get("/kyc/pending")
def get_pending_kyc(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get pending KYC submissions (admin only)"""
    kyc_list = db.query(KYC).filter(
        KYC.status == "pending"
    ).order_by(KYC.submitted_at.asc()).all()
    
    result = []
    for kyc in kyc_list:
        user = db.query(User).filter(User.id == kyc.user_id).first()
        result.append({
            "kyc_id": kyc.id,
            "user_id": kyc.user_id,
            "username": user.username,
            "email": user.email,
            "first_name": kyc.first_name,
            "last_name": kyc.last_name,
            "document_type": kyc.document_type,
            "document_number": kyc.document_number,
            "submitted_at": kyc.submitted_at
        })
    
    return result

@router.post("/kyc/{kyc_id}/approve")
def approve_kyc(
    kyc_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Approve KYC submission (admin only)"""
    kyc = db.query(KYC).filter(KYC.id == kyc_id).first()
    
    if not kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC record not found"
        )
    
    # Update KYC
    kyc.status = "verified"
    kyc.verified_at = datetime.utcnow()
    
    # Update user
    user = db.query(User).filter(User.id == kyc.user_id).first()
    user.kyc_status = "approved"
    user.kyc_approved_at = datetime.utcnow()
    
    # Mark queue item as completed
    queue_item = db.query(UserQueue).filter(
        (UserQueue.user_id == user.id) & 
        (UserQueue.request_type == "kyc_review") &
        (UserQueue.status != "completed")
    ).first()
    
    if queue_item:
        queue_item.status = "completed"
        queue_item.updated_at = datetime.utcnow()
        db.add(queue_item)
    
    db.add(kyc)
    db.add(user)
    db.commit()
    
    emit_event_notification(
        db,
        user_id=user.id,
        event_type="kyc_approved",
        title="KYC Approved",
        message="Your KYC application has been approved.",
        data={
            "kyc_id": kyc.id,
            "user_id": user.id
        }
    )
    
    return {"message": "KYC approved successfully"}

@router.post("/kyc/{kyc_id}/reject")
def reject_kyc(
    kyc_id: int,
    rejection_reason: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reject KYC submission (admin only)"""
    kyc = db.query(KYC).filter(KYC.id == kyc_id).first()
    
    if not kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC record not found"
        )
    
    # Update KYC
    kyc.status = "rejected"
    kyc.rejection_reason = rejection_reason
    
    # Update user
    user = db.query(User).filter(User.id == kyc.user_id).first()
    user.kyc_status = "rejected"
    
    # Mark queue item as completed
    queue_item = db.query(UserQueue).filter(
        (UserQueue.user_id == user.id) & 
        (UserQueue.request_type == "kyc_review") &
        (UserQueue.status != "completed")
    ).first()
    
    if queue_item:
        queue_item.status = "completed"
        queue_item.updated_at = datetime.utcnow()
        db.add(queue_item)
    
    db.add(kyc)
    db.add(user)
    db.commit()
    
    emit_event_notification(
        db,
        user_id=user.id,
        event_type="kyc_rejected",
        title="KYC Rejected",
        message=f"Your KYC application was rejected: {rejection_reason}",
        data={
            "kyc_id": kyc.id,
            "user_id": user.id,
            "reason": rejection_reason
        }
    )
    
    return {"message": "KYC rejected"}

# Withdrawal Management

@router.get("/withdrawals/pending")
def get_pending_withdrawals(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get pending withdrawal requests (admin only)"""
    withdrawals = db.query(Withdrawal).filter(
        Withdrawal.status == "pending"
    ).order_by(Withdrawal.requested_at.asc()).all()
    
    result = []
    for withdrawal in withdrawals:
        user = db.query(User).filter(User.id == withdrawal.user_id).first()
        result.append({
            "withdrawal_id": withdrawal.id,
            "user_id": withdrawal.user_id,
            "username": user.username,
            "email": user.email,
            "amount": withdrawal.amount,
            "currency": withdrawal.currency,
            "bank_account": withdrawal.bank_account,
            "requested_at": withdrawal.requested_at
        })
    
    return result

@router.post("/withdrawals/{withdrawal_id}/approve")
def approve_withdrawal(
    withdrawal_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Approve withdrawal request (admin only)"""
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    
    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Withdrawal not found"
        )
    
    # Update withdrawal
    withdrawal.status = "approved"
    withdrawal.approved_at = datetime.utcnow()
    
    # Update user
    user = db.query(User).filter(User.id == withdrawal.user_id).first()
    
    # Mark queue item as completed
    queue_item = db.query(UserQueue).filter(
        (UserQueue.user_id == user.id) & 
        (UserQueue.request_type == "withdrawal") &
        (UserQueue.status != "completed")
    ).first()
    
    if queue_item:
        queue_item.status = "completed"
        queue_item.updated_at = datetime.utcnow()
        db.add(queue_item)
    
    db.add(withdrawal)
    db.commit()
    
    emit_event_notification(
        db,
        user_id=user.id,
        event_type="withdrawal_approved",
        title="Withdrawal Approved",
        message=f"Your withdrawal request for ${withdrawal.amount:.2f} has been approved.",
        data={
            "withdrawal_id": withdrawal.id,
            "amount": withdrawal.amount,
            "currency": withdrawal.currency
        }
    )
    
    return {"message": "Withdrawal approved"}

@router.post("/withdrawals/{withdrawal_id}/reject")
def reject_withdrawal(
    withdrawal_id: int,
    rejection_reason: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reject withdrawal request (admin only)"""
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    
    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Withdrawal not found"
        )
    
    # Update withdrawal
    withdrawal.status = "rejected"
    withdrawal.rejection_reason = rejection_reason
    
    # Update user
    user = db.query(User).filter(User.id == withdrawal.user_id).first()
    
    # Mark queue item as completed
    queue_item = db.query(UserQueue).filter(
        (UserQueue.user_id == user.id) & 
        (UserQueue.request_type == "withdrawal") &
        (UserQueue.status != "completed")
    ).first()
    
    if queue_item:
        queue_item.status = "completed"
        queue_item.updated_at = datetime.utcnow()
        db.add(queue_item)
    
    db.add(withdrawal)
    db.commit()

    emit_event_notification(
        db,
        user_id=user.id,
        event_type="withdrawal_rejected",
        title="Withdrawal Rejected",
        message=f"Your withdrawal request for ${withdrawal.amount:.2f} was rejected: {rejection_reason}",
        data={
            "withdrawal_id": withdrawal.id,
            "amount": withdrawal.amount,
            "currency": withdrawal.currency,
            "reason": rejection_reason
        }
    )
    
    return {"message": "Withdrawal rejected"}

# Card Request Management

@router.get("/card-requests/pending")
def get_pending_card_requests(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get pending card issuance requests (admin only)"""
    card_requests = db.query(CardRequest).filter(
        CardRequest.status == "pending"
    ).order_by(CardRequest.requested_at.asc()).all()

    result = []
    for request in card_requests:
        user = db.query(User).filter(User.id == request.user_id).first()
        result.append({
            "request_id": request.id,
            "user_id": request.user_id,
            "username": user.username,
            "email": user.email,
            "account_token": request.account_token,
            "card_type": request.card_type,
            "spend_limit": request.spend_limit,
            "spend_limit_duration": request.spend_limit_duration,
            "memo": request.memo,
            "requested_at": request.requested_at
        })

    return result

@router.post("/card-requests/{request_id}/approve")
def approve_card_request(
    request_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Approve a pending card issuance request (admin only)"""
    card_request = db.query(CardRequest).filter(CardRequest.id == request_id).first()
    if not card_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card request not found"
        )
    if card_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card request is not pending"
        )

    cardholder = db.query(Cardholder).filter(
        Cardholder.account_token == card_request.account_token
    ).first()
    if not cardholder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cardholder not found"
        )

    lithic_response = lithic_client.create_card(
        account_token=card_request.account_token,
        card_type=card_request.card_type,
        spend_limit=int(card_request.spend_limit or 0),
        spend_limit_duration=card_request.spend_limit_duration,
        memo=card_request.memo
    )

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

    card_request.status = "approved"
    card_request.approved_at = datetime.utcnow()

    queue_item = db.query(UserQueue).filter(
        (UserQueue.user_id == card_request.user_id) &
        (UserQueue.request_type == "card_issue") &
        (UserQueue.status != "completed")
    ).first()
    if queue_item:
        queue_item.status = "completed"
        queue_item.updated_at = datetime.utcnow()
        db.add(queue_item)

    db.add(db_card)
    db.add(card_request)
    db.commit()

    user = db.query(User).filter(User.id == card_request.user_id).first()
    if user:
        email_service.send_card_request_approved_email(
            user.email,
            user.username,
            card_request.card_type,
            card_request.memo or ''
        )
        emit_event_notification(
            db,
            user_id=user.id,
            event_type="card_issued",
            title="Card Issued",
            message="Your card request has been approved and a new virtual card has been issued.",
            data={
                "card_token": db_card.card_token,
                "card_type": db_card.card_type
            }
        )

    return {
        "message": "Card request approved",
        "card_token": db_card.card_token
    }

@router.post("/card-requests/{request_id}/reject")
def reject_card_request(
    request_id: int,
    rejection_reason: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reject a pending card issuance request (admin only)"""
    card_request = db.query(CardRequest).filter(CardRequest.id == request_id).first()
    if not card_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card request not found"
        )
    if card_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card request is not pending"
        )

    card_request.status = "rejected"
    card_request.rejected_at = datetime.utcnow()
    card_request.rejection_reason = rejection_reason

    queue_item = db.query(UserQueue).filter(
        (UserQueue.user_id == card_request.user_id) &
        (UserQueue.request_type == "card_issue") &
        (UserQueue.status != "completed")
    ).first()
    if queue_item:
        queue_item.status = "completed"
        queue_item.updated_at = datetime.utcnow()
        db.add(queue_item)

    db.add(card_request)
    db.commit()

    user = db.query(User).filter(User.id == card_request.user_id).first()
    if user:
        email_service.send_card_request_rejected_email(
            user.email,
            user.username,
            card_request.card_type,
            rejection_reason
        )
        emit_event_notification(
            db,
            user_id=user.id,
            event_type="card_rejected",
            title="Card Request Rejected",
            message=f"Your card request was rejected: {rejection_reason}",
            data={
                "request_id": card_request.id,
                "reason": rejection_reason
            }
        )

    return {"message": "Card request rejected"}

# User Management

@router.get("/users")
def list_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "email_verified": user.email_verified,
            "kyc_status": user.kyc_status,
            "is_active": user.is_active,
            "created_at": user.created_at
        })
    
    return result

@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Deactivate user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    db.add(user)
    db.commit()
    
    return {"message": "User deactivated"}

@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Activate user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.add(user)
    db.commit()
    
    return {"message": "User activated"}

# Card Management

@router.get("/cards")
def list_all_cards(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all cards (admin only)"""
    cards = db.query(Card).offset(skip).limit(limit).all()
    
    result = []
    for card in cards:
        cardholder = db.query(Cardholder).filter(Cardholder.account_token == card.account_token).first()
        user = None
        if cardholder:
            user = db.query(User).filter(User.email == cardholder.email).first()
        result.append({
            "card_token": card.card_token,
            "account_token": card.account_token,
            "card_type": card.card_type,
            "status": card.status,
            "spend_limit": card.spend_limit,
            "updated_at": card.updated_at,
            "username": user.username if user else (cardholder.email if cardholder else "Unknown")
        })
    
    return result

@router.put("/cards/{card_token}/freeze")
def freeze_card(
    card_token: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Freeze a card (admin only)"""
    card = db.query(Card).filter(Card.card_token == card_token).first()
    
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    # Call Lithic to freeze
    lithic_client.freeze_card(card_token)
    
    card.status = "frozen"
    card.updated_at = datetime.utcnow()
    db.add(card)
    db.commit()

    cardholder = db.query(Cardholder).filter(Cardholder.account_token == card.account_token).first()
    if cardholder:
        user = db.query(User).filter(User.email == cardholder.email).first()
        if user:
            emit_event_notification(
                db,
                user_id=user.id,
                event_type="card_frozen",
                title="Card Frozen",
                message="Your card has been frozen by an administrator.",
                data={"card_token": card.card_token}
            )
    
    return {"message": "Card frozen"}

@router.put("/cards/{card_token}/unfreeze")
def unfreeze_card(
    card_token: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Unfreeze a card (admin only)"""
    card = db.query(Card).filter(Card.card_token == card_token).first()
    
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    # Call Lithic to unfreeze
    lithic_client.unfreeze_card(card_token)
    
    card.status = "active"
    card.updated_at = datetime.utcnow()
    db.add(card)
    db.commit()

    cardholder = db.query(Cardholder).filter(Cardholder.account_token == card.account_token).first()
    if cardholder:
        user = db.query(User).filter(User.email == cardholder.email).first()
        if user:
            emit_event_notification(
                db,
                user_id=user.id,
                event_type="card_unfrozen",
                title="Card Unfrozen",
                message="Your card has been unfrozen by an administrator.",
                data={"card_token": card.card_token}
            )
    
    return {"message": "Card unfrozen"}
