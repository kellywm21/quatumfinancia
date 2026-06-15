from fastapi import APIRouter, Depends, HTTPException
from src.services.lithic_service import lithic_client
from src.services.auth_service import get_current_active_user

router = APIRouter(prefix="/api/financial-accounts", tags=["financial-accounts"])


@router.get("/{financial_account_token}")
def get_financial_account(
    financial_account_token: str,
    current_user = Depends(get_current_active_user)
):
    """Return balance and details for a financial account token"""
    try:
        balance = lithic_client.get_financial_account(financial_account_token)
        return balance
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
