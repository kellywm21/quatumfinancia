from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, ForeignKey, Text, Enum
from datetime import datetime
from src.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    two_factor_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, nullable=True, unique=True)
    kyc_status = Column(String, default="pending")  # pending, submitted, approved, rejected
    kyc_data = Column(String, nullable=True)  # JSON string with KYC info
    kyc_submitted_at = Column(DateTime, nullable=True)
    kyc_approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Cardholder(Base):
    __tablename__ = "cardholders"
    
    id = Column(Integer, primary_key=True, index=True)
    account_token = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    business_name = Column(String, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    amount = Column(Float)
    currency = Column(String, default="USD")
    status = Column(String, default="pending")
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Card(Base):
    __tablename__ = "cards"
    
    id = Column(Integer, primary_key=True, index=True)
    card_token = Column(String, unique=True, index=True)
    account_token = Column(String, index=True)  # Link to cardholder
    financial_account_token = Column(String, nullable=True)
    pan = Column(String, nullable=True)  # Last 4 digits stored
    cvv = Column(String, nullable=True)  # Masked for security
    exp_month = Column(Integer, nullable=True)
    exp_year = Column(Integer, nullable=True)
    card_type = Column(String, default="VIRTUAL")  # VIRTUAL or PHYSICAL
    status = Column(String, default="active")
    spend_limit = Column(Float, nullable=True)  # In cents
    spend_limit_duration = Column(String, default="MONTHLY")
    memo = Column(String, nullable=True)
    pin_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CardRequest(Base):
    __tablename__ = "card_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    account_token = Column(String, index=True)
    card_type = Column(String, default="VIRTUAL")
    spend_limit = Column(Float, nullable=True)
    spend_limit_duration = Column(String, default="MONTHLY")
    memo = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    requested_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Withdrawal(Base):
    __tablename__ = "withdrawals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    amount = Column(Float)
    currency = Column(String, default="USD")
    status = Column(String, default="pending")  # pending, approved, rejected, completed
    bank_account = Column(String)  # Masked bank account
    memo = Column(String, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)

class KYC(Base):
    __tablename__ = "kyc_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    date_of_birth = Column(String)  # YYYY-MM-DD
    country = Column(String)
    document_type = Column(String)  # passport, driver_license, id_card
    document_number = Column(String)
    address = Column(String)
    city = Column(String)
    postal_code = Column(String)
    id_document_path = Column(String, nullable=True)
    selfie_path = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, verified, rejected
    submitted_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)

class EmailVerification(Base):
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    token = Column(String, unique=True, index=True)
    email = Column(String, index=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    verified_at = Column(DateTime, nullable=True)

class UserQueue(Base):
    __tablename__ = "user_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    status = Column(String, default="pending")  # pending, processing, completed
    queue_priority = Column(Integer, default=0)  # Higher number = higher priority
    request_type = Column(String)  # withdrawal, kyc_review, account_update
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DepositAddress(Base):
    __tablename__ = "deposit_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    currency = Column(String, default="BTC")  # BTC, ETH, USDC, etc.
    address = Column(String, unique=True, index=True)
    qr_code_data = Column(String)  # Base64 encoded QR code image
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

class TransactionPin(Base):
    __tablename__ = "transaction_pins"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    pin_hash = Column(String)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CardProvider(Base):
    __tablename__ = "card_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # lithic, stripe, etc.
    api_key = Column(String)
    api_secret = Column(String)
    base_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class FundsAccount(Base):
    __tablename__ = "funds_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    provider_id = Column(Integer, ForeignKey("card_providers.id"), index=True)
    account_token = Column(String, unique=True, index=True)
    balance = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    status = Column(String, default="active")  # active, frozen, closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PendingApproval(Base):
    __tablename__ = "pending_approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    approval_type = Column(String)  # deposit, withdrawal, card_fund, kyc
    reference_id = Column(String, index=True)  # ID of the related record
    amount = Column(Float, nullable=True)
    currency = Column(String, default="USD")
    status = Column(String, default="pending")  # pending, approved, rejected, expired
    eta_minutes = Column(Integer, default=30)  # Estimated time in minutes
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

class Wallet(Base):
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    wallet_id = Column(String, unique=True, index=True)  # Internal wallet identifier
    encrypted_seed = Column(String)  # Encrypted wallet seed/private key
    status = Column(String, default="active")  # active, frozen, locked
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WalletBalance(Base):
    __tablename__ = "wallet_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), index=True)
    currency = Column(String, index=True)  # BTC, ETH, USDC, USDT, etc.
    balance = Column(Float, default=0.0)
    available_balance = Column(Float, default=0.0)  # Balance available for spending
    locked_balance = Column(Float, default=0.0)  # Balance locked in pending transactions
    last_sync = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WalletAddress(Base):
    __tablename__ = "wallet_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), index=True)
    currency = Column(String, index=True)  # BTC, ETH, USDC, USDT, etc.
    address = Column(String, unique=True, index=True)
    derivation_path = Column(String)  # HD wallet derivation path
    label = Column(String, nullable=True)  # User-defined label
    is_change = Column(Boolean, default=False)  # Change address or receiving address
    used_count = Column(Integer, default=0)  # How many times this address has received funds
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CryptoTransaction(Base):
    __tablename__ = "crypto_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), index=True)
    tx_hash = Column(String, unique=True, index=True)  # Blockchain transaction hash
    currency = Column(String, index=True)
    tx_type = Column(String)  # send, receive, internal_transfer
    amount = Column(Float)
    fee = Column(Float, default=0.0)
    from_address = Column(String, nullable=True)
    to_address = Column(String)
    confirmations = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, confirmed, failed
    block_height = Column(Integer, nullable=True)
    block_hash = Column(String, nullable=True)
    memo = Column(String, nullable=True)
    internal_tx_id = Column(String, nullable=True)  # For internal transfers
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

class InternalTransfer(Base):
    __tablename__ = "internal_transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    from_wallet_id = Column(Integer, ForeignKey("wallets.id"), index=True)
    to_wallet_id = Column(Integer, ForeignKey("wallets.id"), index=True)
    currency = Column(String, index=True)
    amount = Column(Float)
    fee = Column(Float, default=0.0)
    status = Column(String, default="pending")  # pending, completed, failed
    memo = Column(String, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CryptoSettings(Base):
    __tablename__ = "crypto_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    currency = Column(String, unique=True, index=True)
    name = Column(String)  # Full name (Bitcoin, Ethereum, etc.)
    symbol = Column(String)  # Symbol (BTC, ETH, etc.)
    decimals = Column(Integer, default=8)
    contract_address = Column(String, nullable=True)  # For ERC-20 tokens
    network = Column(String)  # mainnet, testnet
    min_confirmations = Column(Integer, default=1)
    fee_per_kb = Column(Float, nullable=True)  # For UTXO coins
    gas_price = Column(Float, nullable=True)  # For Ethereum
    gas_limit = Column(Integer, nullable=True)  # For Ethereum
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WithdrawalApprovalTier(Base):
    __tablename__ = "withdrawal_approval_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    tier_name = Column(String, unique=True, index=True)  # instant, standard, premium
    min_amount = Column(Float, default=0.0)
    max_amount = Column(Float, nullable=True)  # None = unlimited
    auto_approve = Column(Boolean, default=False)  # Auto-approve or require admin review
    processing_time_hours = Column(Integer, default=24)
    requires_pin = Column(Boolean, default=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AccountRejection(Base):
    __tablename__ = "account_rejections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    rejection_reason = Column(String)  # kyc_failed, suspicious_activity, compliance_issue, etc.
    rejection_details = Column(Text, nullable=True)  # Detailed explanation
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who rejected
    can_appeal = Column(Boolean, default=True)
    appeal_deadline = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active, appealed, resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NotificationTrigger(Base):
    __tablename__ = "notification_triggers"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True)  # user_signup, kyc_approved, withdrawal_completed, card_issued, etc.
    trigger_name = Column(String)  # Human-readable name
    email_template = Column(String)  # Email template file path
    send_email = Column(Boolean, default=True)
    send_in_app = Column(Boolean, default=True)
    priority = Column(String, default="normal")  # low, normal, high, urgent
    retry_on_failure = Column(Boolean, default=True)
    max_retries = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TransactionHistory(Base):
    __tablename__ = "transaction_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=True, index=True)
    tx_type = Column(String)  # deposit, withdrawal, card_fund, transfer, etc.
    amount = Column(Float)
    currency = Column(String)
    status = Column(String)  # pending, confirmed, failed
    blockchain_hash = Column(String, nullable=True, unique=True, index=True)  # For on-chain txs
    block_explorer_url = Column(String, nullable=True)  # Direct link to block explorer
    from_address = Column(String, nullable=True)
    to_address = Column(String, nullable=True)
    fee = Column(Float, default=0.0)
    description = Column(String, nullable=True)
    tx_metadata = Column(String, nullable=True)  # JSON with additional details
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

class CardManagement(Base):
    __tablename__ = "card_management"
    
    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(String, ForeignKey("cards.card_token"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    is_frozen = Column(Boolean, default=False)
    freeze_reason = Column(String, nullable=True)  # manual, suspected_fraud, etc.
    frozen_at = Column(DateTime, nullable=True)
    spend_limit = Column(Float, nullable=True)
    spend_limit_period = Column(String, default="monthly")  # daily, weekly, monthly
    transaction_count = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    event_type = Column(String, index=True)
    title = Column(String)
    message = Column(String)
    data = Column(String, nullable=True)  # JSON with additional context
    email_sent = Column(Boolean, default=False)
    in_app_sent = Column(Boolean, default=False)
    read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
