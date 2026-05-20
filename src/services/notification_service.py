from datetime import datetime
from sqlalchemy.orm import Session
from src.models.payment import User, NotificationTrigger, Notification
from src.services.email_service import send_email


def emit_event_notification(
    db: Session,
    user_id: int,
    event_type: str,
    title: str,
    message: str,
    data: dict | None = None
) -> Notification:
    """Emit a user notification and send email if the trigger is configured."""
    trigger = db.query(NotificationTrigger).filter(
        NotificationTrigger.event_type == event_type,
        NotificationTrigger.is_active == True
    ).first()

    recipient = db.query(User).filter(User.id == user_id).first()
    if not recipient:
        raise ValueError(f"Recipient user with id {user_id} not found")

    notification = Notification(
        user_id=user_id,
        event_type=event_type,
        title=title,
        message=message,
        data=str(data) if data else None,
        in_app_sent=bool(trigger and trigger.send_in_app),
        email_sent=False,
        created_at=datetime.utcnow(),
        sent_at=None
    )

    if trigger and trigger.send_email:
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
        except Exception as exc:
            print(f"Notification email failed for event '{event_type}': {exc}")

    notification.sent_at = datetime.utcnow()
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification
