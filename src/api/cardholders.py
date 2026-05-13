from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.payment import CardholderCreate, CardholderResponse
from src.models.payment import Cardholder
from src.services.lithic_service import lithic_client
from src.services.auth_service import get_current_active_user
from src.models.payment import User

router = APIRouter(prefix="/api/cardholders", tags=["cardholders"])

@router.post("/", response_model=CardholderResponse)
def create_cardholder(
    cardholder: CardholderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new cardholder/account via Lithic"""
    try:
        # Check if cardholder already exists
        existing = db.query(Cardholder).filter(Cardholder.email == cardholder.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create cardholder via Lithic API
        lithic_response = lithic_client.create_cardholder(
            email=cardholder.email,
            business_name=cardholder.business_name
        )
        
        # Save to database
        db_cardholder = Cardholder(
            account_token=lithic_response["account_token"],
            email=lithic_response["email"],
            business_name=cardholder.business_name,
            status=lithic_response["status"]
        )
        db.add(db_cardholder)
        db.commit()
        db.refresh(db_cardholder)
        return db_cardholder
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{account_token}", response_model=CardholderResponse)
def get_cardholder(account_token: str, db: Session = Depends(get_db)):
    """Get cardholder details"""
    cardholder = db.query(Cardholder).filter(Cardholder.account_token == account_token).first()
    if not cardholder:
        raise HTTPException(status_code=404, detail="Cardholder not found")
    return cardholder

@router.get("/")
def list_cardholders(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """List all cardholders"""
    cardholders = db.query(Cardholder).offset(skip).limit(limit).all()
    return cardholders
