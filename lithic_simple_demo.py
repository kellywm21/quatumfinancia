#!/usr/bin/env python3
"""
Lithic Virtual Card Issuance - Python Version
Based on the JavaScript example from lithic.com
"""

import os
from lithic import Lithic

# Load API key from environment
LITHIC_API_KEY = os.getenv("LITHIC_API_KEY", "your_api_key_here")
lithic = Lithic(api_key=LITHIC_API_KEY)

def issue_virtual_card():
    """Issue a real virtual Mastercard using Lithic API"""

    print("🏦 Lithic Virtual Card Issuance Demo")
    print("=" * 50)

    try:
        # STEP 1: Create account/cardholder
        print("\n[1] Creating account...")
        account = lithic.accounts.create(
            email="business@advancia.com"
        )
        print(f"✅ Account created: {account.token}")

        # STEP 2: Issue virtual card instantly
        print("\n[2] Issuing virtual Mastercard...")
        card = lithic.cards.create(
            type="VIRTUAL",
            account_token=account.token,
            spend_limit=15000000,  # $150,000 in cents
            spend_limit_duration="MONTHLY",
            memo="Advancia Business Elite"
        )

        print("✅ Virtual card issued!")
        print(f"   PAN: {card.pan}")  # Real 16-digit card number
        print(f"   CVV: {card.cvv}")  # Real CVV2
        print(f"   Expiry: {card.exp_month}/{card.exp_year}")
        print(f"   Card Token: {card.token}")

        # STEP 3: Fund the card (optional - requires funding account)
        print("\n[3] Funding card...")
        try:
            # Note: This requires a source financial account token
            # In sandbox, you might need to set up a funding account first
            funding_result = lithic.financial_accounts.load(
                financial_account_token=card.financial_account_token,
                amount=8432000,  # $84,320 in cents
                memo="Initial card funding via ACH"
            )
            print(f"✅ Card funded with ${84320.00:,.2f}")
        except Exception as e:
            print(f"⚠️  Funding not available in sandbox: {e}")
            print("   In production, integrate with ACH/payment processors")

        print("\n🎉 SUCCESS: Real virtual Mastercard ready!")
        print("   Usable at any Mastercard merchant worldwide")
        print(f"   Card Number: **** **** **** {card.pan[-4:]}")

        return {
            "account_token": account.token,
            "card_token": card.token,
            "pan": card.pan,
            "cvv": card.cvv,
            "exp_month": card.exp_month,
            "exp_year": card.exp_year
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # Check API key
    if LITHIC_API_KEY == "your_api_key_here":
        print("❌ Please set your LITHIC_API_KEY environment variable")
        print("   Get your FREE API key at https://lithic.com")
        exit(1)

    result = issue_virtual_card()
    if result:
        print(f"\n💾 Card details saved to result: {result}")