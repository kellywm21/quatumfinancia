"""
Lithic Card Issuance Demo with Authentication
Issue a virtual card and fund it in minutes (with JWT authentication)
"""

import asyncio
import requests
import json
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:8000"

def demo_complete_card_flow():
    """Complete authenticated flow: Login → Create cardholder → Issue card → Fund card"""

    print("\n" + "="*70)
    print("LITHIC VIRTUAL CARD ISSUANCE DEMO (WITH AUTHENTICATION)")
    print("="*70)

    # STEP 0: Authentication
    print("\n[STEP 0] Authenticating...")

    # First try to register (if user doesn't exist)
    register_data = {
        "email": "demo@advancia.com",
        "username": "demo",
        "password": "demopassword123",
        "full_name": "Demo User"
    }

    register_response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if register_response.status_code == 200:
        print("✅ Demo user registered!")
    elif register_response.status_code == 400 and ("already exists" in register_response.json().get("detail", "").lower() or "already registered" in register_response.json().get("detail", "").lower()):
        print("✅ Demo user already exists, proceeding to login...")
    else:
        print(f"❌ Registration failed: {register_response.json()}")
        return

    # Login to get access token
    login_data = {
        "username": "demo",
        "password": "demopassword123"
    }

    login_response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.json()}")
        return

    token_data = login_response.json()
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    print("✅ Authentication successful!")
    print(f"   Token: {access_token[:50]}...")

    # STEP 1: Create Cardholder
    print("\n[STEP 1] Creating cardholder...")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    cardholder_data = {
        "email": f"business{timestamp}@advancia.com",
        "business_name": "Advancia Business Elite"
    }

    response = requests.post(f"{BASE_URL}/api/cardholders/", json=cardholder_data, headers=headers)

    if response.status_code != 200:
        print(f"❌ Error: {response.json()}")
        return

    cardholder = response.json()
    account_token = cardholder["account_token"]
    print(f"✅ Cardholder created!")
    print(f"   Account Token: {account_token}")
    print(f"   Email: {cardholder['email']}")

    # STEP 2: Issue Virtual Card
    print("\n[STEP 2] Issuing virtual Mastercard...")
    card_data = {
        "account_token": account_token,
        "card_type": "VIRTUAL",
        "spend_limit": 15000000,  # $150,000 in cents
        "spend_limit_duration": "MONTHLY",
        "memo": "Advancia Business Elite Card"
    }

    response = requests.post(f"{BASE_URL}/api/cards/", json=card_data, headers=headers)

    if response.status_code != 200:
        print(f"❌ Error: {response.json()}")
        return

    card = response.json()
    card_token = card["card_token"]
    print(f"✅ Virtual card issued!")
    print(f"   Card Token: {card_token}")
    print(f"   Card Type: {card['card_type']}")
    print(f"   Spend Limit: ${card['spend_limit']/100:,.2f} {card['spend_limit_duration']}")
    print(f"   Expiry: {card['exp_month']}/{card['exp_year']}")
    print(f"   Last 4 Digits: ****{card['pan']}")

    print("\n🎉 SUCCESS: Virtual card is ready for use!")
    print("   The card can now be used for payments and can be funded via ACH or other methods.")
    print("   In production, you would integrate with payment processors to fund the card.")

    # STEP 3: Check Financial Account Balance
    print("\n[STEP 3] Checking financial account balance...")
    response = requests.get(f"{BASE_URL}/api/financial-accounts/{card['financial_account_token']}", headers=headers)

    if response.status_code == 200:
        balance = response.json()
        print(f"✅ Financial account balance retrieved!")
        print(f"   Available Balance: ${balance.get('available_balance', 0)/100:,.2f}")
        print(f"   Pending Balance: ${balance.get('pending_balance', 0)/100:,.2f}")
    else:
        print(f"⚠️  Could not retrieve balance: {response.json()}")

    # STEP 4: Create a sample payment
    print("\n[STEP 4] Creating a sample payment...")
    payment_data = {
        "amount": 99.99,
        "currency": "USD",
        "description": "Demo transaction - Office supplies"
    }

    response = requests.post(f"{BASE_URL}/api/payments/", json=payment_data, headers=headers)
    if response.status_code == 200:
        payment = response.json()
        print("✅ Sample payment created!")
        print(f"   Transaction ID: {payment['transaction_id']}")
        print(f"   Amount: ${payment['amount']}")
        print(f"   Status: {payment['status']}")
    else:
        print(f"⚠️  Could not create payment: {response.json()}")

    # SUMMARY
    print("\n" + "="*70)
    print("CARD READY TO USE")
    print("="*70)
    print(f"""
Your REAL virtual Mastercard is ready to use:
├─ Card Type: Virtual Mastercard
├─ Last 4 Digits: ****{card['pan']}
├─ Expiry: {card['exp_month']}/{card['exp_year']}
├─ Monthly Spend Limit: ${card['spend_limit']/100:,.2f}
└─ Status: Ready for transactions at any Mastercard merchant

🔐 Authentication Required:
   All API endpoints now require JWT authentication
   Use POST /auth/login to get access tokens

🎯 This card works at:
   ✓ Online merchants
   ✓ In-store retailers
   ✓ ATMs
   ✓ Contactless payments
   ✓ Any Mastercard-accepting merchant worldwide

📊 Next Steps:
   1. Share card details with authorized users
   2. Monitor transactions via API
   3. Add additional spend limits/restrictions
   4. Top-up balance as needed
""")
    
    # SAVE CONFIG
    print("\n[INFO] Card configuration saved locally:")
    config = {
        "cardholder": {
            "account_token": account_token,
            "email": cardholder["email"],
            "business_name": cardholder.get("business_name")
        },
        "card": {
            "token": card_token,
            "last_4": card["pan"],
            "exp_month": card["exp_month"],
            "exp_year": card["exp_year"],
            "type": card["card_type"],
            "financial_account": card["financial_account_token"]
        }
    }
    
    with open("card_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("   File: card_config.json")
    print("\n✅ Demo completed successfully!\n")

if __name__ == "__main__":
    try:
        demo_complete_card_flow()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API at http://localhost:8000")
        print("   Make sure the FastAPI server is running: python -m src.main")
    except Exception as e:
        print(f"❌ Error: {e}")
