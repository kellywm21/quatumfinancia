# QUICK START: Issue Your First Virtual Card

## 3-Minute Setup

### Step 1: Start the Server
```bash
python -m src.main
```
✅ Server running at http://localhost:8000

### Step 2: Create a Cardholder
Open http://localhost:8000/docs and use the **Swagger UI** to:

**POST** `/api/cardholders/`
```json
{
  "email": "business@advancia.com",
  "business_name": "Advancia Business Elite"
}
```

**Response:**
```json
{
  "id": 1,
  "account_token": "account_xyz123...",
  "email": "business@advancia.com",
  "business_name": "Advancia Business Elite",
  "status": "active",
  "created_at": "2026-05-07T12:00:00",
  "updated_at": "2026-05-07T12:00:00"
}
```

👉 **Save the `account_token`** - you'll need it next!

### Step 3: Issue a Virtual Card
**POST** `/api/cards/`
```json
{
  "account_token": "account_xyz123...",
  "card_type": "VIRTUAL",
  "spend_limit": 15000000,
  "spend_limit_duration": "MONTHLY",
  "memo": "Advancia Business Elite Card"
}
```

**Response:**
```json
{
  "id": 1,
  "card_token": "card_xyz456...",
  "account_token": "account_xyz123...",
  "financial_account_token": "fin_acc_xyz...",
  "pan": "1234",
  "cvv": "123",
  "exp_month": 12,
  "exp_year": 2027,
  "card_type": "VIRTUAL",
  "status": "active",
  "spend_limit": 15000000,
  "spend_limit_duration": "MONTHLY",
  "memo": "Advancia Business Elite Card",
  "created_at": "2026-05-07T12:00:00",
  "updated_at": "2026-05-07T12:00:00"
}
```

🎉 **You now have a REAL Mastercard!**
- **Full PAN**: Shown once by Lithic, securely share with cardholder
- **CVV**: 123
- **Expiry**: 12/2027

### Step 4: Fund the Card
**POST** `/api/cards/fund`
```json
{
  "card_token": "card_xyz456...",
  "amount": 8432000,
  "memo": "Initial funding via ACH"
}
```

**Response:**
```json
{
  "card_token": "card_xyz456...",
  "amount_funded": 8432000,
  "status": "success",
  "memo": "Initial funding via ACH"
}
```

✅ **$84,320 loaded to card!** Card is now ready to use.

### Step 5: Check Balance
**GET** `/api/cards/card_xyz456.../balance`

**Response:**
```json
{
  "financial_account_token": "fin_acc_xyz...",
  "available_balance": 8432000,
  "pending_balance": 0
}
```

📊 **$84,320.00 available**

---

## Run the Automated Demo

Instead of manual steps, run:
```bash
python lithic_card_demo.py
```

This automatically:
1. Creates cardholder
2. Issues virtual card  
3. Funds card with $84,320
4. Retrieves and displays balance
5. Saves configuration to `card_config.json`

---

## What Can You Do With This Card?

✅ Use at any Mastercard merchant worldwide
✅ Online shopping
✅ In-store purchases
✅ ATM withdrawals (if configured)
✅ Contactless/NFC payments
✅ Subscription services
✅ B2B payments
✅ International transactions

---

## API Response Codes

| Code | Meaning |
|------|---------|
| 200  | ✅ Success |
| 400  | ❌ Bad request (invalid email, duplicate account, etc.) |
| 404  | ❌ Not found (cardholder/card doesn't exist) |
| 500  | ❌ Server error |

---

## Common Issues

**Q: "Email already registered"**
- Use a different email address or retrieve existing cardholder with GET /api/cardholders/

**Q: "Cardholder not found"**
- Make sure you use the correct `account_token` from Step 2

**Q: "Card financial account not configured"**
- Try creating the card again; financial account is auto-assigned

**Q: "Could not connect to API"**
- Make sure the server is running: `python -m src.main`

---

## Security Reminders

⚠️ **In Production:**
- Use HTTPS only (not HTTP)
- Rotate API keys regularly
- Never log full card PANs
- Implement request rate limiting
- Add authentication to endpoints
- Audit all card operations

✅ **In Sandbox:**
- No real money involved
- Use for testing safely
- Non-production keys only

---

## Next Steps

1. **Store Card Config**
   - Configuration is auto-saved to `card_config.json`
   - Use tokens for subsequent operations

2. **Make Transactions**
   - Track payments via `/api/payments/` endpoints
   - Card automatically processes Mastercard transactions

3. **Add More Features**
   - Set per-transaction limits
   - Implement webhooks for real-time updates
   - Add spending analytics

4. **Go Live**
   - Upgrade to production at lithic.com
   - Update API key in `.env`
   - Enable proper authentication
   - Deploy with SSL/TLS

---

## Need Help?

- 📚 [Lithic API Docs](https://docs.lithic.com)
- 💬 [Lithic Community](https://lithic.com/community)
- 🐛 [Report Issues](mailto:support@advancia.com)

---

**Happy card issuing! 🚀**
