from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.payment import User, EmailVerification, KYC, UserQueue
from src.schemas.payment import UserCreate, UserResponse, Token, EmailVerificationVerify, KYCCreate, KYCResponse
from src.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_current_admin_user,
    get_password_hash,
    settings
)
from src.services.email_service import email_service
import secrets
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with email verification"""
    # Check if user already exists
    db_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    verification_token = secrets.token_urlsafe(32)
    # Only auto-verify in test mode when explicitly allowed (safer for CI)
    email_verified = settings.email_test_mode and settings.allow_auto_verify
    email_verification_token = None if email_verified else verification_token
    
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone_number=user.phone_number,
        email_verification_token=email_verification_token,
        email_verified=email_verified,
        kyc_status="pending"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    if not email_verified:
        # Create email verification record
        expires_at = datetime.utcnow() + timedelta(hours=24)
        email_verification = EmailVerification(
            user_id=db_user.id,
            token=verification_token,
            email=user.email,
            expires_at=expires_at
        )
        db.add(email_verification)
        db.commit()
        
        # Send verification email
        email_service.send_verification_email(
            recipient_email=user.email,
            username=user.username,
            token=verification_token
        )
    else:
        # In test mode with auto-verify allowed, do not send outgoing verification emails
        # but log the intended action via the email service (it already handles test mode)
        email_service.send_verification_email(
            recipient_email=user.email,
            username=user.username,
            token=verification_token
        )
    
    return db_user

@router.post("/verify-email")
def verify_email(verification: EmailVerificationVerify, db: Session = Depends(get_db)):
    """Verify user email"""
    email_verification = db.query(EmailVerification).filter(
        EmailVerification.token == verification.token
    ).first()
    
    if not email_verification:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    if email_verification.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token has expired")
    
    if email_verification.verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    # Update user
    user = db.query(User).filter(User.id == email_verification.user_id).first()
    user.email_verified = True
    user.email_verification_token = None
    
    # Update email verification
    email_verification.verified = True
    email_verification.verified_at = datetime.utcnow()
    
    db.add(user)
    db.add(email_verification)
    db.commit()
    
    return {"message": "Email verified successfully. Please complete KYC to activate your account."}

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )
    
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

@router.post("/google", response_model=Token)
def google_auth(token: str, db: Session = Depends(get_db)):
    """Authenticate with Google OAuth token"""
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            "309765497606-ub6ion23nh6id0p60aqtdinjnit33pse.apps.googleusercontent.com"
        )
        
        # Extract user info
        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])
        
        # Check if user exists
        user = db.query(User).filter(User.google_id == google_id).first()
        if not user:
            # Check if email exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                # Link Google account
                existing_user.google_id = google_id
                user = existing_user
            else:
                # Create new user
                user = User(
                    email=email,
                    username=name.replace(' ', '_').lower(),
                    hashed_password="",  # No password for OAuth
                    full_name=name,
                    google_id=google_id,
                    email_verified=True,  # Google emails are verified
                    kyc_status="pending"
                )
                db.add(user)
        
        db.commit()
        db.refresh(user)
        
        # Generate access token
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

@router.get("/pending-approvals")
def get_pending_approvals(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's pending approvals"""
    approvals = []
    
    # Check KYC status
    kyc = db.query(KYC).filter(
        (KYC.user_id == current_user.id) & (KYC.status == "pending")
    ).first()
    if kyc:
        approvals.append({
            "id": f"kyc_{kyc.id}",
            "approval_type": "kyc_verification",
            "user_email": current_user.email,
            "amount": None,
            "currency": None,
            "created_at": kyc.submitted_at,
            "status": "pending",
            "eta_minutes": 1440  # 24 hours
        })
    
    # Check pending withdrawals
    from src.models.payment import Withdrawal
    withdrawals = db.query(Withdrawal).filter(
        (Withdrawal.user_id == current_user.id) & (Withdrawal.status == "pending")
    ).all()
    for w in withdrawals:
        approvals.append({
            "id": f"withdrawal_{w.id}",
            "approval_type": "withdrawal",
            "user_email": current_user.email,
            "amount": str(w.amount),
            "currency": w.currency,
            "created_at": w.requested_at,
            "status": "pending",
            "eta_minutes": 60  # 1 hour
        })
    
    # Check pending card requests
    from src.models.payment import CardRequest
    card_requests = db.query(CardRequest).filter(
        (CardRequest.user_id == current_user.id) & (CardRequest.status == "pending")
    ).all()
    for cr in card_requests:
        approvals.append({
            "id": f"card_request_{cr.id}",
            "approval_type": "card_request",
            "user_email": current_user.email,
            "amount": None,
            "currency": None,
            "created_at": cr.requested_at,
            "status": "pending",
            "eta_minutes": 120  # 2 hours
        })
    
    return approvals
