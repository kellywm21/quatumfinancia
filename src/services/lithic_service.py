from lithic import Lithic
from src.config import settings
from typing import Dict, Any

class LithicAPIClient:
    def __init__(self):
        self.client = Lithic(
            api_key=settings.lithic_api_key,
            base_url=settings.lithic_api_base_url,
            environment="sandbox" if "sandbox" in settings.lithic_api_base_url else "production"
        )
    
    # Cardholder/Account Operations
    def create_cardholder(self, email: str, business_name: str = None) -> Dict[str, Any]:
        """Create a new cardholder account"""
        from datetime import datetime
        
        # Simplified individual account creation
        account_holder_data = {
            "first_name": "Business",
            "last_name": "Account",
            "email": email,
            "phone_number": "+15555555555",  # E.164 format
            "address": {
                "address1": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94105",
                "country": "USA"
            },
            "workflow": "KYC_EXEMPT",  # Use KYC exempt workflow for testing
            "kyc_exemption_type": "AUTHORIZED_USER"
        }
        
        account_holder = self.client.account_holders.create(**account_holder_data)

        return {
            "account_token": account_holder.account_token,  # Use account_token instead of token
            "email": account_holder_data.get("email", account_holder_data.get("individual", {}).get("email", "unknown@example.com")),
            "status": "active"
        }
    
    def get_cardholder(self, account_token: str) -> Dict[str, Any]:
        """Retrieve cardholder details"""
        account_holder = self.client.account_holders.retrieve(account_token)
        return {
            "account_token": account_holder.token,
            "email": account_holder.email,
            "status": "active"
        }
    
    # Card Operations
    def create_card(
        self, 
        account_token: str,
        card_type: str = "VIRTUAL",
        spend_limit: int = 15000000,  # $150,000 in cents
        spend_limit_duration: str = "MONTHLY",
        memo: str = None
    ) -> Dict[str, Any]:
        """Create a new virtual card"""
        card_data = {
            "type": card_type,
            "account_token": account_token,
            "spend_limit": spend_limit,
            "spend_limit_duration": spend_limit_duration,
        }
        if memo:
            card_data["memo"] = memo
        
        card = self.client.cards.create(**card_data)

        return {
            "card_token": card.token,
            "account_token": account_token,
            "financial_account_token": getattr(card, 'financial_account_token', account_token),  # Fallback to account_token
            "pan": card.pan[-4:] if card.pan else None,  # Store last 4 digits only
            "cvv": card.cvv,
            "exp_month": card.exp_month,
            "exp_year": card.exp_year,
            "card_type": card_type,
            "status": "active",
            "spend_limit": spend_limit,
            "spend_limit_duration": spend_limit_duration,
            "memo": memo
        }
    
    def get_card(self, card_token: str) -> Dict[str, Any]:
        """Retrieve card details"""
        card = self.client.cards.retrieve(card_token)
        return {
            "card_token": card.token,
            "pan": card.pan[-4:] if card.pan else None,
            "exp_month": card.exp_month,
            "exp_year": card.exp_year,
            "status": card.status,
        }
    
    def list_cards(self, account_holder_token: str = None) -> list:
        """List cards, optionally filtered by account holder"""
        if account_holder_token:
            cards = self.client.cards.list(account_holder_tokens=[account_holder_token])
        else:
            cards = self.client.cards.list()
        
        return [
            {
                "card_token": card.token,
                "pan": card.pan[-4:] if card.pan else None,
                "status": card.status,
            }
            for card in cards.data
        ]
    
    # Funding Operations
    def fund_card(
        self, 
        financial_account_token: str,
        amount: int,  # In cents
        memo: str = None
    ) -> Dict[str, Any]:
        """Fund a card via financial account"""
        fund_data = {
            "financial_account_token": financial_account_token,
            "amount": amount,
        }
        if memo:
            fund_data["memo"] = memo
        
        result = self.client.financial_accounts.load(**fund_data)
        return {
            "financial_account_token": financial_account_token,
            "amount": amount,
            "status": "success",
            "memo": memo
        }
    
    def get_financial_account(self, financial_account_token: str) -> Dict[str, Any]:
        """Get financial account balance and details"""
        account = self.client.financial_accounts.retrieve(financial_account_token)
        return {
            "financial_account_token": account.token,
            "available_balance": account.available_balance,
            "pending_balance": account.pending_balance,
        }

# Create global client instance
lithic_client = LithicAPIClient()
