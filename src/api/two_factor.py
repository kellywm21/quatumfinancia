from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import random
import time
from src.services.auth_service import get_current_active_user
from src.models.payment import User
from src.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/2fa", tags=["2fa"])

class Enable2FARequest(BaseModel):
    phone_number: str

class Verify2FARequest(BaseModel):
    code: str

class TwoFactorResponse(BaseModel):
    enabled: bool
    phone_number: Optional[str] = None
    message: str

# In-memory store for demo (in production, use Redis or database)
otp_store = {}

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_sms_otp(phone_number: str, otp: str) -> bool:
    """Send OTP via SMS (simulated for demo)"""
    # In production, integrate with Twilio, AWS SNS, etc.
    print(f"SMS to {phone_number}: Your verification code is {otp}")
    return True

@router.post("/enable", response_model=TwoFactorResponse)
def enable_2fa(
    request: Enable2FARequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enable 2FA for the current user"""
    try:
        # Generate OTP
        otp = generate_otp()

        # Store OTP with expiration (5 minutes)
        otp_store[current_user.id] = {
            "otp": otp,
            "phone_number": request.phone_number,
            "expires": time.time() + 300  # 5 minutes
        }

        # Send SMS (simulated)
        send_sms_otp(request.phone_number, otp)

        return TwoFactorResponse(
            enabled=False,
            phone_number=request.phone_number,
            message="Verification code sent to your phone. Please verify to enable 2FA."
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify", response_model=TwoFactorResponse)
def verify_2fa(
    request: Verify2FARequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Verify 2FA code and enable 2FA"""
    try:
        # Check if OTP exists and is valid
        if current_user.id not in otp_store:
            raise HTTPException(status_code=400, detail="No pending 2FA setup")

        stored_data = otp_store[current_user.id]

        if time.time() > stored_data["expires"]:
            del otp_store[current_user.id]
            raise HTTPException(status_code=400, detail="OTP expired")

        if request.code != stored_data["otp"]:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        # Enable 2FA for user
        current_user.phone_number = stored_data["phone_number"]
        current_user.two_factor_enabled = True
        db.add(current_user)
        db.commit()

        # Clean up
        del otp_store[current_user.id]

        return TwoFactorResponse(
            enabled=True,
            phone_number=current_user.phone_number,
            message="2FA has been successfully enabled"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/disable")
def disable_2fa(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA for the current user"""
    try:
        current_user.two_factor_enabled = False
        db.add(current_user)
        db.commit()

        return {"message": "2FA has been disabled"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status", response_model=TwoFactorResponse)
def get_2fa_status(current_user: User = Depends(get_current_active_user)):
    """Get 2FA status for current user"""
    return TwoFactorResponse(
        enabled=current_user.two_factor_enabled or False,
        phone_number=current_user.phone_number,
        message="2FA is enabled" if current_user.two_factor_enabled else "2FA is not enabled"
    )