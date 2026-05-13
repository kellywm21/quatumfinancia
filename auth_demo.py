#!/usr/bin/env python3
"""
Authentication Test Script
Demonstrates JWT authentication flow with the Advancia Payledger API
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    """Test the complete authentication and card issuance flow"""

    print("🔐 Advancia Payledger Authentication Demo")
    print("=" * 50)

    # Step 1: Register a new user
    print("\n[1] Registering new user...")
    register_data = {
        "email": "admin@advancia.com",
        "username": "admin",
        "password": "securepassword123",
        "full_name": "Admin User"
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code == 200:
        print("✅ User registered successfully!")
        user = response.json()
        print(f"   User ID: {user['id']}")
        print(f"   Username: {user['username']}")
        print(f"   Email: {user['email']}")
    else:
        print(f"❌ Registration failed: {response.json()}")

    # Step 2: Login to get access token
    print("\n[2] Logging in...")
    login_data = {
        "username": "admin",
        "password": "securepassword123"
    }

    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data["access_token"]
        print("✅ Login successful!")
        print(f"   Token Type: {token_data['token_type']}")
        print(f"   Token: {access_token[:50]}...")

        # Set authorization header for subsequent requests
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 3: Get user profile
        print("\n[3] Getting user profile...")
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if response.status_code == 200:
            profile = response.json()
            print("✅ Profile retrieved!")
            print(f"   Full Name: {profile['full_name']}")
            print(f"   Is Admin: {profile['is_admin']}")
        else:
            print(f"❌ Profile retrieval failed: {response.json()}")

        # Step 4: Create a cardholder (now requires auth)
        print("\n[4] Creating cardholder...")
        cardholder_data = {
            "email": f"business{hash('test') % 10000}@advancia.com",  # Unique email
            "business_name": "Test Business Corp"
        }

        response = requests.post(f"{BASE_URL}/api/cardholders/", json=cardholder_data, headers=headers)
        if response.status_code == 200:
            cardholder = response.json()
            account_token = cardholder["account_token"]
            print("✅ Cardholder created!")
            print(f"   Account Token: {account_token}")
            print(f"   Email: {cardholder['email']}")
        else:
            print(f"❌ Cardholder creation failed: {response.json()}")
            return

        # Step 5: Issue a virtual card
        print("\n[5] Issuing virtual Mastercard...")
        card_data = {
            "account_token": account_token,
            "card_type": "VIRTUAL",
            "spend_limit": 10000000,  # $100,000
            "spend_limit_duration": "MONTHLY",
            "memo": "Test Virtual Card"
        }

        response = requests.post(f"{BASE_URL}/api/cards/", json=card_data, headers=headers)
        if response.status_code == 200:
            card = response.json()
            print("✅ Virtual card issued!")
            print(f"   Card Token: {card['card_token']}")
            print(f"   Last 4 Digits: ****{card['pan']}")
            print(f"   Expiry: {card['exp_month']}/{card['exp_year']}")
            print(f"   Spend Limit: ${card['spend_limit']/100:,.2f} {card['spend_limit_duration']}")
        else:
            print(f"❌ Card issuance failed: {response.json()}")

        # Step 6: Create a payment (requires auth)
        print("\n[6] Creating a payment...")
        payment_data = {
            "amount": 49.99,
            "currency": "USD",
            "description": "Test transaction"
        }

        response = requests.post(f"{BASE_URL}/api/payments/", json=payment_data, headers=headers)
        if response.status_code == 200:
            payment = response.json()
            print("✅ Payment created!")
            print(f"   Transaction ID: {payment['transaction_id']}")
            print(f"   Amount: ${payment['amount']}")
            print(f"   Status: {payment['status']}")
        else:
            print(f"❌ Payment creation failed: {response.json()}")

    else:
        print(f"❌ Login failed: {response.json()}")

    print("\n🎉 Authentication demo completed!")
    print("\n📋 API Endpoints now secured with JWT:")
    print("   • POST /auth/register - Register new user")
    print("   • POST /auth/login - Get access token")
    print("   • GET /auth/me - Get current user profile")
    print("   • POST /api/cardholders/ - Create cardholder (auth required)")
    print("   • POST /api/cards/ - Issue virtual card (auth required)")
    print("   • POST /api/payments/ - Create payment (auth required)")

def test_unauthorized_access():
    """Test that endpoints require authentication"""
    print("\n🚫 Testing unauthorized access...")

    # Try to create cardholder without auth
    response = requests.post(f"{BASE_URL}/api/cardholders/", json={
        "email": "test@example.com",
        "business_name": "Test"
    })

    if response.status_code == 401:
        print("✅ Unauthorized access properly blocked!")
        print(f"   Response: {response.json()}")
    else:
        print(f"❌ Unexpected response: {response.status_code} - {response.json()}")

if __name__ == "__main__":
    try:
        test_auth_flow()
        test_unauthorized_access()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API at http://localhost:8000")
        print("   Make sure the FastAPI server is running: python -m src.main")
    except Exception as e:
        print(f"❌ Error: {e}")