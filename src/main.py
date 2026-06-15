from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from src.config import settings
from src.database import Base, engine
from src.api import payments, cards, cardholders, auth, kyc, withdrawals, admin, deposits, transaction_pin, funds, wallet, fiat_onramp, withdrawal_tiers, two_factor, account_rejection, notifications, transaction_history, financial_accounts

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(kyc.router)
app.include_router(withdrawals.router)
app.include_router(withdrawal_tiers.router)
app.include_router(two_factor.router)
app.include_router(fiat_onramp.router)
app.include_router(deposits.router)
app.include_router(transaction_pin.router)
app.include_router(funds.router)
app.include_router(wallet.router)
app.include_router(transaction_history.router)
app.include_router(admin.router)
app.include_router(cardholders.router)
app.include_router(cards.router)
app.include_router(payments.router)
app.include_router(financial_accounts.router)
app.include_router(account_rejection.router)
app.include_router(notifications.router)

@app.get("/")
def read_root():
    return {"message": "Payment Processing API", "version": settings.app_version}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Serve HTML files
html_files = ["login", "register", "verify-email", "kyc", "wallet_dashboard", "admin_panel", "pending_approvals", "deposit_address", "transaction_pin", "card_management", "buy_crypto", "twofa_settings"]

for file in html_files:
    app.get(f"/{file}")(lambda file=file: FileResponse(f"./{file}.html", media_type="text/html"))
    app.get(f"/{file}.html")(lambda file=file: FileResponse(f"./{file}.html", media_type="text/html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
