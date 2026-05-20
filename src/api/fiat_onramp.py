from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
from src.services.auth_service import get_current_active_user
from src.models.payment import User

router = APIRouter(prefix="/api/fiat", tags=["fiat-onramp"])

class FiatPurchaseRequest(BaseModel):
    currency: str  # BTC, ETH, USDC, etc.
    amount: float  # Amount in fiat currency (USD)
    payment_method: str  # credit_card, bank_transfer, etc.

class FiatPurchaseResponse(BaseModel):
    purchase_id: str
    currency: str
    amount: float
    fiat_amount: float
    status: str
    payment_url: Optional[str] = None

# MoonPay API configuration (in production, use environment variables)
MOONPAY_API_KEY = "test_api_key"  # Replace with actual API key
MOONPAY_BASE_URL = "https://api.moonpay.com"

@router.post("/purchase", response_model=FiatPurchaseResponse)
def create_fiat_purchase(
    purchase: FiatPurchaseRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create a fiat-to-crypto purchase via MoonPay"""
    try:
        # In production, this would integrate with MoonPay API
        # For demo purposes, we'll simulate the response

        # Calculate crypto amount based on current rates (simplified)
        crypto_amount = calculate_crypto_amount(purchase.currency, purchase.amount)

        # Create purchase record (in production, this would be stored in database)
        purchase_response = FiatPurchaseResponse(
            purchase_id=f"moonpay_{current_user.id}_{purchase.currency}",
            currency=purchase.currency,
            amount=crypto_amount,
            fiat_amount=purchase.amount,
            status="pending",
            payment_url=f"https://buy.moonpay.com?apiKey={MOONPAY_API_KEY}&currencyCode={purchase.currency}&walletAddress={current_user.wallet_address}"
        )

        return purchase_response

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rates")
def get_crypto_rates():
    """Get current crypto-to-fiat exchange rates"""
    try:
        # In production, fetch from CoinGecko or similar API
        # For demo, return static rates
        rates = {
            "BTC": 45000,
            "ETH": 3000,
            "USDC": 1.00,
            "USDT": 1.00
        }
        return {"rates": rates, "base_currency": "USD"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def calculate_crypto_amount(currency: str, fiat_amount: float) -> float:
    """Calculate crypto amount from fiat amount (simplified)"""
    rates = {
        "BTC": 45000,  # 1 BTC = $45,000
        "ETH": 3000,   # 1 ETH = $3,000
        "USDC": 1.00,  # 1 USDC = $1
        "USDT": 1.00   # 1 USDT = $1
    }

    rate = rates.get(currency, 1.0)
    return fiat_amount / rate