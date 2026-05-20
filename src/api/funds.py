from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.payment import User, CardProvider, FundsAccount, PendingApproval
from src.schemas.payment import CardProviderCreate, CardProviderResponse, FundsAccountCreate, FundsAccountResponse
from src.services.auth_service import get_current_active_user, get_current_admin_user

router = APIRouter(prefix="/api/card-providers", tags=["card-providers"])

@router.post("/", response_model=CardProviderResponse)
def create_card_provider(
    provider: CardProviderCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new card provider (admin only)"""
    
    # Check if provider already exists
    existing = db.query(CardProvider).filter(CardProvider.name == provider.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card provider already exists"
        )
    
    card_provider = CardProvider(
        name=provider.name,
        api_key=provider.api_key,
        api_secret=provider.api_secret,
        base_url=provider.base_url,
        is_active=True
    )
    
    db.add(card_provider)
    db.commit()
    db.refresh(card_provider)
    
    return card_provider

@router.get("/", response_model=list[CardProviderResponse])
def list_card_providers(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all card providers (admin only)"""
    
    providers = db.query(CardProvider).filter(CardProvider.is_active == True).all()
    return providers

@router.post("/funds-account", response_model=FundsAccountResponse)
def create_funds_account(
    account_data: FundsAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a funds account for user"""
    
    # Check if provider exists
    provider = db.query(CardProvider).filter(
        (CardProvider.id == account_data.provider_id) &
        (CardProvider.is_active == True)
    ).first()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card provider not found"
        )
    
    # Check if user already has a funds account for this provider
    existing = db.query(FundsAccount).filter(
        (FundsAccount.user_id == current_user.id) &
        (FundsAccount.provider_id == account_data.provider_id)
    ).first()
    
    if existing:
        return existing
    
    # In real implementation, this would call the provider's API to create an account
    # For demo, we'll generate a mock account token
    import secrets
    account_token = f"acct_{secrets.token_hex(16)}"
    
    funds_account = FundsAccount(
        user_id=current_user.id,
        provider_id=account_data.provider_id,
        account_token=account_token,
        balance=0.0,
        currency=account_data.currency,
        status="active"
    )
    
    db.add(funds_account)
    db.commit()
    db.refresh(funds_account)
    
    return funds_account

@router.get("/funds-accounts", response_model=list[FundsAccountResponse])
def list_funds_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's funds accounts"""
    
    accounts = db.query(FundsAccount).filter(
        (FundsAccount.user_id == current_user.id) &
        (FundsAccount.status == "active")
    ).all()
    
    return accounts

@router.get("/funds-accounts/{account_id}", response_model=FundsAccountResponse)
def get_funds_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific funds account"""
    
    account = db.query(FundsAccount).filter(
        (FundsAccount.id == account_id) &
        (FundsAccount.user_id == current_user.id)
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funds account not found"
        )
    
    return account

@router.post("/funds-accounts/{account_id}/fund")
def fund_account(
    account_id: int,
    amount: float,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Request to fund a card account"""
    
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    account = db.query(FundsAccount).filter(
        (FundsAccount.id == account_id) &
        (FundsAccount.user_id == current_user.id) &
        (FundsAccount.status == "active")
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funds account not found"
        )
    
    # Create pending approval for funding
    expires_at = datetime.utcnow() + timedelta(hours=24)
    pending_approval = PendingApproval(
        user_id=current_user.id,
        approval_type="card_fund",
        reference_id=str(account_id),
        amount=amount,
        currency=account.currency,
        status="pending",
        eta_minutes=15,  # Quick approval for card funding
        expires_at=expires_at
    )
    
    db.add(pending_approval)
    db.commit()
    
    return {
        "message": "Funding request submitted for approval",
        "approval_id": pending_approval.id,
        "eta_minutes": pending_approval.eta_minutes
    }
