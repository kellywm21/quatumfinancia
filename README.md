# Advancia Payledger - Payment Processing API with Authentication

[![CI](https://github.com/kellywm21/quatumfinancia/actions/workflows/ci.yml/badge.svg)](https://github.com/kellywm21/quatumfinancia/actions/workflows/ci.yml)
[![CI Dispatch](https://github.com/kellywm21/quatumfinancia/actions/workflows/ci-dispatch.yml/badge.svg)](https://github.com/kellywm21/quatumfinancia/actions/workflows/ci-dispatch.yml)
[![E2E Windows](https://github.com/kellywm21/quatumfinancia/actions/workflows/e2e-windows.yml/badge.svg)](https://github.com/kellywm21/quatumfinancia/actions/workflows/e2e-windows.yml)

A FastAPI-based payment processing platform with Lithic card issuance
integration and JWT authentication.

## ✨ Features

- **🔐 JWT Authentication**: Secure user authentication with access tokens
- **🎫 Virtual Card Issuance**: Issue real Mastercard virtual cards instantly
- **💳 Card Management**: Create, fund, and manage virtual cards
- **👥 Cardholder Management**: Manage business cardholder accounts
- **💰 Payment Processing**: Process payments and transactions
- **📊 Transaction Tracking**: Monitor payments and card activity
- **🛡️ Security**: All API endpoints protected with authentication
- **🗄️ Database**: SQLAlchemy ORM with PostgreSQL (Supabase)
- **✅ Validation**: Pydantic models for type-safe requests/responses
- **🚀 CI/CD**: GitHub Actions for automated testing

## Project Structure

```
advancia-payledger/
├── src/
│   ├── api/              # FastAPI route handlers
│   │   ├── cardholders.py   # Cardholder/account endpoints
│   │   ├── cards.py         # Card issuance & funding
│   │   └── payments.py      # Payment processing
│   ├── models/           # SQLAlchemy database models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── services/         # Lithic API client service
│   ├── config.py         # Configuration management
│   ├── database.py       # Database setup
│   └── main.py           # FastAPI application entry point
├── tests/                # Test suite
├── lithic_card_demo.py   # Complete card issuance demo
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
└── README.md            # This file
```

## Setup

### 1. Prerequisites

- Python 3.11+
- Lithic API Key (free sandbox at <https://lithic.com>)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file from `.env.example` and update these values:
```
LITHIC_API_KEY=
LITHIC_API_BASE_URL=https://sandbox.lithic.com
USE_MOCK_LITHIC=true
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production-123456789
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./payments.db
```

If you want to use a real Lithic sandbox key, set `LITHIC_API_KEY` to that value and set `USE_MOCK_LITHIC=false`.

If you want to use PostgreSQL instead of local SQLite, override `DATABASE_URL` with your database connection string:
```
DATABASE_URL=postgresql://postgres:<YOUR-PASSWORD>@db.example.com:5432/postgres
```

> Make sure you replace `<YOUR-PASSWORD>` with your actual database password.

### Use Mock Lithic (Recommended for local testing)
If you do not have a valid Lithic sandbox API key, keep:
```
USE_MOCK_LITHIC=true
LITHIC_API_KEY=
```
This will bypass real Lithic API calls and still let you exercise authentication, cardholder creation, card issuance, funding, and balance endpoints locally.

### Manual CI Dispatch
A manual CI workflow is available at `ci-dispatch.yml`. Use it to run the full test suite on demand without waiting for a push or pull request.

- Workflow file: `.github/workflows/ci-dispatch.yml`
- Trigger: `workflow_dispatch`
- Uses PostgreSQL service and runs `python -m pytest -q`

### Test mode and auto-verify

For CI and E2E testing we provide a test mode that can auto-verify newly registered users to simplify automated flows. This is gated behind two environment variables:

- `EMAIL_TEST_MODE=true` — enables test-mode behavior in the app.
- `ALLOW_AUTO_VERIFY=true` — must be explicitly set to allow auto-verification of newly registered users.

Both variables must be set for auto-verification to occur. This reduces the risk of accidental auto-verification in production. The E2E workflow sets `ALLOW_AUTO_VERIFY=true` only for test runs.

Before promoting to production, remove `ALLOW_AUTO_VERIFY` usage and ensure real email verification is enforced. See issue #2 for tracking.

### 4. Run the Application
```bash
python -m src.main
```

The server starts at **http://localhost:8000**

## Authentication

All API endpoints require JWT authentication. First, register and login to get an access token:

### Register User
```bash
POST /auth/register
{
  "email": "user@company.com",
  "username": "username",
  "password": "securepassword",
  "full_name": "User Name"
}
```

### Login
```bash
POST /auth/login
Form data:
username=username&password=securepassword

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Use API with Authentication
Include the Authorization header in all requests:
```
Authorization: Bearer <access_token>
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get access token
- `GET /auth/me` - Get current user profile (requires auth)

### Cardholders (Requires Authentication)
Create and manage business accounts:

```bash
# Create a new cardholder
POST /api/cardholders/
Authorization: Bearer <token>
{
  "email": "business@company.com",
  "business_name": "Company Inc"
}

# Get cardholder details
GET /api/cardholders/{account_token}
Authorization: Bearer <token>

# List all cardholders
GET /api/cardholders/
Authorization: Bearer <token>
```

### Virtual Cards (Requires Authentication)
Issue and manage cards:

```bash
# Issue a virtual Mastercard
POST /api/cards/
Authorization: Bearer <token>
{
  "account_token": "account_token_here",
  "card_type": "VIRTUAL",
  "spend_limit": 15000000,        # $150,000 in cents
  "spend_limit_duration": "MONTHLY",
  "memo": "Business card"
}

# Fund a card (load balance)
POST /api/cards/fund
Authorization: Bearer <token>
{
  "card_token": "card_token_here",
  "amount": 8432000,              # $84,320 in cents
  "memo": "Initial funding"
}

# Get card balance
GET /api/cards/{card_token}/balance
Authorization: Bearer <token>

# Get card details
GET /api/cards/{card_token}
Authorization: Bearer <token>

# List cards
GET /api/cards/
Authorization: Bearer <token>
```

### Payments (Requires Authentication)
Track payment transactions:

```bash
# Create a payment
POST /api/payments/
Authorization: Bearer <token>
{
  "amount": 100.0,
  "currency": "USD",
  "description": "Payment description"
}

# Get payment details
GET /api/payments/{transaction_id}
Authorization: Bearer <token>

# List payments
GET /api/payments/
Authorization: Bearer <token>
```

## Quick Start Demo

Run the complete authenticated card issuance flow:

```bash
# Terminal 1: Start the API server
python -m src.main

# Terminal 2: Run the demo
python lithic_card_demo.py
```

This will:
1. 🔐 Register/login a demo user and get JWT token
2. ✅ Create a cardholder account (authenticated)
3. ✅ Issue a virtual card (mock or real Lithic depending on config)
4. ✅ Create a sample payment (authenticated)
5. ✅ Check financial account balance
6. ✅ Display card details
7. ✅ Save configuration to `card_config.json`

Or run the authentication test:

```bash
python auth_demo.py
```

This demonstrates the complete authentication flow and API usage.

## Verification Checklist

Use this repo and verify the flow in the current project with these commands:

1. Start the server:
```bash
python -m src.main
```
2. Register a user:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@advancia.com","username":"demo","password":"demopassword123","full_name":"Demo User"}'
```
3. Login and capture the token:
```bash
curl -X POST http://localhost:8000/auth/login \
  -d 'username=demo&password=demopassword123'
```
4. Create a cardholder:
```bash
curl -X POST http://localhost:8000/api/cardholders/ \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"email":"business@advancia.com","business_name":"Advancia Business"}'
```
5. Issue a card:
```bash
curl -X POST http://localhost:8000/api/cards/ \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"account_token":"<account_token>","card_type":"VIRTUAL","spend_limit":15000000,"spend_limit_duration":"MONTHLY","memo":"Demo card"}'
```
6. Check the mock financial account balance:
```bash
curl -X GET http://localhost:8000/api/financial-accounts/<financial_account_token> \
  -H 'Authorization: Bearer <token>'
```

> The current repo is fine to use; no new repository is needed unless you want a completely fresh start.

## CI / GitHub Actions

This repository includes two GitHub Actions workflows:

- `ci.yml` (.github/workflows/ci.yml): runs on `ubuntu-latest`, installs dependencies and runs `pytest`.
- `e2e-windows.yml` (.github/workflows/e2e-windows.yml): runs on `windows-latest`, starts the API server and runs the `verify_demo.ps1` verification script.

Required repository secrets (add in GitHub > Settings > Secrets > Actions):

- `JWT_SECRET_KEY` — secret used for signing JWTs in CI/E2E (string).
- `LITHIC_API_KEY` — optional Lithic sandbox API key (leave empty for mock mode). For E2E we recommend keeping `USE_MOCK_LITHIC=true` so production keys are not required.

Workflow triggers:

- Both workflows run on `push` and `pull_request` targeting `main`.

Notes:

- The E2E job uses mock Lithic mode by default (`USE_MOCK_LITHIC=true`). If you wish to test against real Lithic sandbox, set `USE_MOCK_LITHIC=false` and provide `LITHIC_API_KEY` as a repository secret.
- GitHub Actions already provides a built-in `GITHUB_TOKEN` — do not share personal access tokens in repo files or in chat.


## JavaScript Example (Reference)

For comparison, here's the equivalent JavaScript/Node.js code:

```javascript
// STEP 1: Sign up at lithic.com → get API key → sandbox is FREE
// STEP 2: Install SDK: npm install lithic
// STEP 3: Issue your first real virtual card

import Lithic from 'lithic';

const lithic = new Lithic({ apiKey: 'YOUR_LITHIC_API_KEY' });

// Create cardholder
const account = await lithic.accounts.create({
  email: 'business@advancia.com',
});

// Issue virtual card instantly — REAL Mastercard PAN returned
const card = await lithic.cards.create({
  type: 'VIRTUAL',
  account_token: account.token,
  spend_limit: 150000_00,  // $150,000 in cents
  spend_limit_duration: 'MONTHLY',
  memo: 'Advancia Business Elite',
});

console.log(card.pan);    // Real 16-digit card number
console.log(card.cvv);    // Real CVV2
console.log(card.exp_month); // Expiry month
console.log(card.exp_year);  // Expiry year

// Fund the card (load balance)
await lithic.financialAccounts.load({
  financial_account_token: card.financial_account_token,
  amount: 84320_00,  // $84,320 in cents
  memo: 'Initial card funding via ACH',
});

// Result: REAL card. REAL balance. Usable at any Mastercard merchant.
```

**Note**: The Python implementation uses `account_holders.create` instead of `accounts.create` for proper KYC handling, and funding is implemented via book transfers in production environments.

This will:
1. ✅ Create a cardholder account
2. ✅ Issue a real virtual Mastercard
3. ✅ Check account balance
4. ✅ Display card details
5. ✅ Save configuration to `card_config.json`

Expected output:
```
======================================================================
LITHIC VIRTUAL CARD ISSUANCE DEMO
======================================================================

[STEP 1] Creating cardholder...
✅ Cardholder created!
   Account Token: account_xyz...
   Email: business20260509030740@advancia.com

[STEP 2] Issuing virtual Mastercard...
✅ Virtual card issued!
   Card Token: card_xyz...
   Card Type: VIRTUAL
   Spend Limit: $150,000.00 MONTHLY
   Expiry: 5/2031
   Last 4 Digits: ****1234

🎉 SUCCESS: Virtual card is ready for use!
   The card can now be used for payments and can be funded via ACH or other methods.
   In production, you would integrate with payment processors to fund the card.

[STEP 3] Checking financial account balance...
✅ Financial account balance retrieved!
   Available Balance: $0.00
   Pending Balance: $0.00

======================================================================
CARD READY TO USE
======================================================================

Your REAL virtual Mastercard is ready to use:
├─ Card Type: Virtual Mastercard
├─ Last 4 Digits: ****1234
├─ Expiry: 5/2031
├─ Monthly Spend Limit: $150,000.00
└─ Status: Ready for transactions at any Mastercard merchant

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

[INFO] Card configuration saved locally:
   File: card_config.json

✅ Demo completed successfully!
```

## API Documentation

Visit **http://localhost:8000/docs** (Swagger UI) for interactive API testing

## Testing

Run the test suite:
```bash
pytest
```

Run specific tests:
```bash
pytest tests/test_main.py -v
```

## Configuration

Edit `src/config.py` to customize:

```python
class Settings(BaseSettings):
    lithic_api_key: str              # Your Lithic API key
    lithic_api_base_url: str         # Lithic API endpoint
    database_url: str                # Database connection
    host: str = "0.0.0.0"            # Server host
    port: int = 8000                 # Server port
    debug: bool = False              # Debug mode
```

## Card Details Returned

When you issue a card, Lithic returns:

```json
{
  "card_token": "unique_token",
  "pan": "1234",              // Last 4 digits only (PCI compliance)
  "cvv": "123",               // Security code
  "exp_month": 12,            // Expiration month
  "exp_year": 2027,           // Expiration year
  "status": "active",
  "spend_limit": 15000000,    // Monthly limit in cents
  "card_type": "VIRTUAL"      // Virtual Mastercard
}
```

**IMPORTANT**: The full 16-digit PAN is returned by Lithic once and should be securely stored/transmitted to cardholders. The API only stores last-4 for security.

## Use Cases

### 1. Business Expense Management
```python
# Issue per-employee cards with individual spend limits
# Track and reconcile expenses automatically
# Revoke cards instantly if needed
```

### 2. Vendor Payment Automation
```python
# Create cards for specific vendors
# Set spending limits per transaction type
# Audit all transactions in real-time
```

### 3. Multi-currency Operations
```python
# Issue cards for different regions
# Load balances in local currency
# Track FX rates and costs
```

### 4. Development/Testing
```python
# Free sandbox environment
# Test card creation, funding, and transactions
# No real charges - 100% safe
```

## Security Notes

⚠️ **PCI Compliance**:
- Never log or store full card PANs
- Always use HTTPS in production
- Rotate API keys regularly
- Implement rate limiting on endpoints

✅ **This Implementation**:
- Stores only last-4 digits in database
- Masks CVV in responses
- Full PAN only visible once during issuance
- Environment-based API key management

## Sandbox vs Production

### Sandbox (Development)
```bash
# Free tier - unlimited cards, $1M monthly limit
LITHIC_API_KEY=sandbox_key_...
LITHIC_API_BASE_URL=https://sandbox.lithic.com
```

### Production
```bash
# After verifying account with Lithic
LITHIC_API_KEY=prod_key_...
LITHIC_API_BASE_URL=https://api.lithic.com
```

## Support & Resources

- 📚 [Lithic API Documentation](https://docs.lithic.com)
- 🎓 [Python SDK Guide](https://github.com/lithic-com/lithic-python)
- 💬 [Lithic Community](https://lithic.com/community)
- 📧 [Advancia Support](mailto:support@advancia.com)

## License

MIT License - see LICENSE file for details

---

**Ready to issue your first virtual card?** Run the demo above! 🚀
