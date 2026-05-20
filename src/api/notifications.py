from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.payment import User, NotificationTrigger, Notification
from src.schemas.payment import NotificationTriggerCreate, NotificationTriggerResponse, NotificationResponse
from src.services.auth_service import get_current_active_user, get_current_admin_user
from src.services.email_service import send_email

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# Default notification triggers mapping
DEFAULT_TRIGGERS = {
    "user_signup": {
        "trigger_name": "New User Registration",
        "email_template": "welcome",
        "description": "Sent when a user creates a new account"
    },
    "email_verified": {
        "trigger_name": "Email Verified",
        "email_template": "email_verified",
        "description": "Sent when user verifies their email"
    },
    "kyc_submitted": {
        "trigger_name": "KYC Submission Received",
        "email_template": "kyc_submitted",
        "description": "Sent when user submits KYC documents"
    },
    "kyc_approved": {
        "trigger_name": "KYC Approved",
        "email_template": "kyc_approved",
        "priority": "high",
        "description": "Sent when user's KYC is approved"
    },
    "kyc_rejected": {
        "trigger_name": "KYC Rejected",
        "email_template": "kyc_rejected",
        "priority": "urgent",
        "description": "Sent when user's KYC is rejected"
    },
    "account_rejected": {
        "trigger_name": "Account Rejected",
        "email_template": "account_rejection",
        "priority": "urgent",
        "description": "Sent when user account application is rejected"
    },
    "account_appeal_submitted": {
        "trigger_name": "Appeal Submitted",
        "email_template": "appeal_submitted",
        "description": "Sent when user appeals rejection decision"
    },
    "withdrawal_requested": {
        "trigger_name": "Withdrawal Requested",
        "email_template": "withdrawal_requested",
        "description": "Sent when user requests a withdrawal"
    },
    "withdrawal_pending": {
        "trigger_name": "Withdrawal Pending",
        "email_template": "withdrawal_pending",
        "description": "Sent when withdrawal is awaiting approval"
    },
    "withdrawal_approved": {
        "trigger_name": "Withdrawal Approved",
        "email_template": "withdrawal_approved",
        "priority": "high",
        "description": "Sent when withdrawal is approved"
    },
    "withdrawal_rejected": {
        "trigger_name": "Withdrawal Rejected",
        "email_template": "withdrawal_rejected",
        "description": "Sent when withdrawal is rejected"
    },
    "withdrawal_completed": {
        "trigger_name": "Withdrawal Completed",
        "email_template": "withdrawal_completed",
        "priority": "high",
        "description": "Sent when withdrawal is successfully processed"
    },
    "card_issued": {
        "trigger_name": "Virtual Card Issued",
        "email_template": "card_issued",
        "priority": "high",
        "description": "Sent when virtual card is created"
    },
    "card_rejected": {
        "trigger_name": "Card Request Rejected",
        "email_template": "card_rejected",
        "description": "Sent when a card request is rejected"
    },
    "card_frozen": {
        "trigger_name": "Card Frozen",
        "email_template": "card_frozen",
        "priority": "urgent",
        "description": "Sent when user freezes their card"
    },
    "card_unfrozen": {
        "trigger_name": "Card Unfrozen",
        "email_template": "card_unfrozen",
        "description": "Sent when user unfreezes their card"
    },
    "deposit_received": {
        "trigger_name": "Deposit Received",
        "email_template": "deposit_received",
        "priority": "high",
        "description": "Sent when crypto deposit is received"
    },
    "deposit_confirmed": {
        "trigger_name": "Deposit Confirmed",
        "email_template": "deposit_confirmed",
        "priority": "high",
        "description": "Sent when deposit achieves full confirmations"
    },
    "transaction_sent": {
        "trigger_name": "Transaction Sent",
        "email_template": "transaction_sent",
        "description": "Sent when user sends crypto"
    },
    "transaction_received": {
        "trigger_name": "Transaction Received",
        "email_template": "transaction_received",
        "priority": "high",
        "description": "Sent when user receives crypto"
    },
    "transaction_failed": {
        "trigger_name": "Transaction Failed",
        "email_template": "transaction_failed",
        "priority": "urgent",
        "description": "Sent when transaction fails"
    },
    "pin_changed": {
        "trigger_name": "PIN Changed",
        "email_template": "pin_changed",
        "description": "Sent when user changes transaction PIN"
    },
    "suspicious_activity": {
        "trigger_name": "Suspicious Activity Detected",
        "email_template": "suspicious_activity",
        "priority": "urgent",
        "description": "Sent when suspicious activity is detected"
    }
}

@router.post("/triggers/setup")
def setup_default_triggers(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Initialize default notification triggers (admin only)"""
    
    created_triggers = []
    
    for event_type, config in DEFAULT_TRIGGERS.items():
        # Check if trigger already exists
        existing = db.query(NotificationTrigger).filter(
            NotificationTrigger.event_type == event_type
        ).first()
        
        if existing:
            continue
        
        trigger = NotificationTrigger(
            event_type=event_type,
            trigger_name=config.get("trigger_name"),
            email_template=config.get("email_template"),
            send_email=True,
            send_in_app=True,
            priority=config.get("priority", "normal"),
            retry_on_failure=True,
            max_retries=3,
            is_active=True
        )
        
        db.add(trigger)
        created_triggers.append(event_type)
    
    db.commit()
    
    return {
        "message": "Default notification triggers setup complete",
        "created_count": len(created_triggers),
        "created_triggers": created_triggers
    }

@router.get("/triggers", response_model=list[NotificationTriggerResponse])
def list_notification_triggers(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all notification triggers (admin only)"""
    
    triggers = db.query(NotificationTrigger).filter(
        NotificationTrigger.is_active == True
    ).all()
    
    return triggers

@router.get("/triggers/{event_type}", response_model=NotificationTriggerResponse)
def get_trigger_config(
    event_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get configuration for a specific trigger"""
    
    trigger = db.query(NotificationTrigger).filter(
        NotificationTrigger.event_type == event_type
    ).first()
    
    if not trigger:
        # Return default if exists
        if event_type in DEFAULT_TRIGGERS:
            config = DEFAULT_TRIGGERS[event_type]
            return {
                "event_type": event_type,
                "trigger_name": config.get("trigger_name"),
                "email_template": config.get("email_template"),
                "send_email": True,
                "send_in_app": True,
                "priority": config.get("priority", "normal"),
                "is_active": True
            }
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found"
        )
    
    return trigger

@router.post("/triggers/{event_type}/update")
def update_trigger_config(
    event_type: str,
    config_updates: dict,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update notification trigger configuration (admin only)"""
    
    trigger = db.query(NotificationTrigger).filter(
        NotificationTrigger.event_type == event_type
    ).first()
    
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found"
        )
    
    # Update allowed fields
    if "send_email" in config_updates:
        trigger.send_email = config_updates["send_email"]
    if "send_in_app" in config_updates:
        trigger.send_in_app = config_updates["send_in_app"]
    if "priority" in config_updates:
        trigger.priority = config_updates["priority"]
    if "is_active" in config_updates:
        trigger.is_active = config_updates["is_active"]
    if "retry_on_failure" in config_updates:
        trigger.retry_on_failure = config_updates["retry_on_failure"]
    if "max_retries" in config_updates:
        trigger.max_retries = config_updates["max_retries"]
    
    trigger.updated_at = datetime.utcnow()
    
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    
    return trigger

@router.get("/user/all", response_model=list[NotificationResponse])
def get_user_notifications(
    limit: int = 50,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get notifications for current user"""
    
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(Notification.read == False)
    
    notifications = query.order_by(
        Notification.created_at.desc()
    ).limit(limit).all()
    
    return notifications

@router.post("/user/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.read = True
    notification.read_at = datetime.utcnow()
    
    db.add(notification)
    db.commit()
    
    return {"message": "Notification marked as read"}

@router.post("/user/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for current user"""
    
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False
    ).all()
    
    for notification in notifications:
        notification.read = True
        notification.read_at = datetime.utcnow()
        db.add(notification)
    
    db.commit()
    
    return {
        "message": "All notifications marked as read",
        "count": len(notifications)
    }

@router.post("/emit")
def emit_notification(
    user_id: int,
    event_type: str,
    title: str,
    message: str,
    data: dict = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Emit a notification to a user (admin only)"""
    
    # Get trigger config
    trigger = db.query(NotificationTrigger).filter(
        NotificationTrigger.event_type == event_type,
        NotificationTrigger.is_active == True
    ).first()
    
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification trigger not configured for event: {event_type}"
        )
    
    # Get recipient user
    recipient = db.query(User).filter(User.id == user_id).first()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create notification record
    notification = Notification(
        user_id=user_id,
        event_type=event_type,
        title=title,
        message=message,
        data=str(data) if data else None,
        in_app_sent=trigger.send_in_app,
        email_sent=False
    )
    
    # Send email if configured
    if trigger.send_email:
        try:
            send_email(
                to_email=recipient.email,
                subject=title,
                template=trigger.email_template,
                data={
                    "user_name": recipient.full_name or recipient.username,
                    "title": title,
                    "message": message,
                    **(data or {})
                }
            )
            notification.email_sent = True
        except Exception as e:
            # Log error but don't fail
            print(f"Failed to send email: {str(e)}")
    
    notification.sent_at = datetime.utcnow()
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification

@router.get("/event-map")
def get_event_trigger_map(
    current_user: User = Depends(get_current_active_user)
):
    """Get complete map of events to notification triggers"""
    
    return {
        "event_type_to_trigger": DEFAULT_TRIGGERS,
        "event_categories": {
            "user_lifecycle": [
                "user_signup", "email_verified", "account_rejected", "account_appeal_submitted"
            ],
            "kyc": [
                "kyc_submitted", "kyc_approved", "kyc_rejected"
            ],
            "withdrawals": [
                "withdrawal_requested", "withdrawal_pending", "withdrawal_approved",
                "withdrawal_rejected", "withdrawal_completed"
            ],
            "cards": [
                "card_issued", "card_rejected", "card_frozen", "card_unfrozen"
            ],
            "crypto_transactions": [
                "deposit_received", "deposit_confirmed", "transaction_sent",
                "transaction_received", "transaction_failed"
            ],
            "security": [
                "pin_changed", "suspicious_activity"
            ]
        }
    }

@router.get("/user/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications for current user"""
    
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False
    ).count()
    
    return {"unread_count": count}
