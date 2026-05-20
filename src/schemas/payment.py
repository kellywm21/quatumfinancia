from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# Authentication Schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone_number: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    phone_number: Optional[str]
    is_active: bool
    is_admin: bool
    email_verified: bool
    kyc_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Email Verification Schemas
class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailVerificationVerify(BaseModel):
    token: str

# KYC Schemas
class KYCCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str  # YYYY-MM-DD
    country: str
    document_type: str  # passport, driver_license, id_card
    document_number: str
    address: str
    city: str
    postal_code: str

class KYCResponse(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    status: str
    submitted_at: datetime
    verified_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Withdrawal Schemas
class WithdrawalCreate(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    bank_account: str
    memo: Optional[str] = None
    transaction_pin: Optional[str] = None

class WithdrawalResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    currency: str
    status: str
    requested_at: datetime
    approved_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class WithdrawalApprove(BaseModel):
    withdrawal_id: int
    approved: bool
    rejection_reason: Optional[str] = None

# User Queue Schemas
class UserQueueResponse(BaseModel):
    id: int
    user_id: int
    status: str
    request_type: str
    queue_priority: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Deposit Address Schemas
class DepositAddressCreate(BaseModel):
    currency: str = "BTC"

class DepositAddressResponse(BaseModel):
    id: int
    user_id: int
    currency: str
    address: str
    qr_code_data: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Transaction PIN Schemas
class TransactionPinCreate(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6, pattern=r'^\d+$')

class TransactionPinVerify(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6, pattern=r'^\d+$')

class TransactionPinResponse(BaseModel):
    id: int
    user_id: int
    failed_attempts: int
    locked_until: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Card Provider Schemas
class CardProviderCreate(BaseModel):
    name: str
    api_key: str
    api_secret: str
    base_url: str

class CardProviderResponse(BaseModel):
    id: int
    name: str
    base_url: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Funds Account Schemas
class FundsAccountCreate(BaseModel):
    provider_id: int
    currency: str = "USD"

class FundsAccountResponse(BaseModel):
    id: int
    user_id: int
    provider_id: int
    account_token: str
    balance: float
    currency: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Pending Approval Schemas
class PendingApprovalResponse(BaseModel):
    id: int
    user_id: int
    approval_type: str
    reference_id: str
    amount: Optional[float]
    currency: str
    status: str
    eta_minutes: int
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    expires_at: datetime
    
    class Config:
        from_attributes = True

class PendingApprovalUpdate(BaseModel):
    status: str  # approved, rejected
    rejection_reason: Optional[str] = None


# Cardholder Schemas
class CardholderCreate(BaseModel):
    email: EmailStr
    business_name: Optional[str] = None

class CardholderResponse(BaseModel):
    id: int
    account_token: str
    email: str
    business_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CardholderResponse(BaseModel):
    id: int
    account_token: str
    email: str
    business_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Payment Schemas
class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    description: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    transaction_id: str
    amount: float
    currency: str
    status: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Card Schemas
class CardCreate(BaseModel):
    account_token: Optional[str] = None
    card_type: str = "VIRTUAL"
    spend_limit: float = 15000000  # $150,000 in cents
    spend_limit_duration: str = "MONTHLY"
    memo: Optional[str] = None

class CardFund(BaseModel):
    card_token: str
    amount: float = Field(..., gt=0)  # In cents
    memo: Optional[str] = None

class CardPinRequest(BaseModel):
    pin: str

class CardResponse(BaseModel):
    id: int
    card_token: str
    account_token: str
    financial_account_token: Optional[str]
    pan: Optional[str]  # Last 4 digits
    exp_month: Optional[int]
    exp_year: Optional[int]
    card_type: str
    status: str
    spend_limit: Optional[float]
    spend_limit_duration: str
    memo: Optional[str]
    available_balance: Optional[float] = None
    last_four: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CardRequestCreate(BaseModel):
    account_token: Optional[str] = None
    card_type: str = "VIRTUAL"
    spend_limit: float = 15000000
    spend_limit_duration: str = "MONTHLY"
    memo: Optional[str] = None

class CardRequestResponse(BaseModel):
    id: int
    user_id: int
    account_token: str
    card_type: str
    spend_limit: Optional[float]
    spend_limit_duration: str
    memo: Optional[str]
    status: str
    requested_at: datetime
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CardLimitUpdate(BaseModel):
    spend_limit: Optional[float] = None
    spend_limit_duration: Optional[str] = None

# Wallet and Crypto Schemas
class WalletCreate(BaseModel):
    pass  # Wallet creation is handled internally

class WalletResponse(BaseModel):
    id: int
    user_id: int
    wallet_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WalletBalanceResponse(BaseModel):
    id: int
    wallet_id: int
    currency: str
    balance: float
    available_balance: float
    locked_balance: float
    last_sync: datetime

    class Config:
        from_attributes = True

class WalletAddressResponse(BaseModel):
    id: int
    wallet_id: int
    currency: str
    address: str
    label: Optional[str]
    is_change: bool
    used_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CryptoTransactionResponse(BaseModel):
    id: int
    wallet_id: int
    tx_hash: str
    currency: str
    tx_type: str
    amount: float
    fee: float
    from_address: Optional[str]
    to_address: str
    confirmations: int
    status: str
    block_height: Optional[int]
    memo: Optional[str]
    created_at: datetime
    confirmed_at: Optional[datetime]

    class Config:
        from_attributes = True

class InternalTransferCreate(BaseModel):
    to_wallet_id: int
    currency: str
    amount: float
    memo: Optional[str] = None

class InternalTransferResponse(BaseModel):
    id: int
    from_wallet_id: int
    to_wallet_id: int
    currency: str
    amount: float
    fee: float
    status: str
    memo: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class CryptoSettingsResponse(BaseModel):
    id: int
    currency: str
    name: str
    symbol: str
    decimals: int
    contract_address: Optional[str]
    network: str
    min_confirmations: int
    is_active: bool

    class Config:
        from_attributes = True

class SendCryptoRequest(BaseModel):
    to_address: str
    currency: str
    amount: float
    fee_priority: str = "normal"  # low, normal, high
    memo: Optional[str] = None
    transaction_pin: Optional[str] = None

class WalletOverviewResponse(BaseModel):
    wallet: WalletResponse
    balances: List[WalletBalanceResponse]
    recent_transactions: List[CryptoTransactionResponse]
    total_value_usd: float

# Withdrawal Tier Schemas
class WithdrawalApprovalTierCreate(BaseModel):
    tier_name: str
    min_amount: float = 0.0
    max_amount: Optional[float] = None
    auto_approve: bool = False
    processing_time_hours: int = 24
    requires_pin: bool = True
    description: Optional[str] = None

class WithdrawalApprovalTierResponse(BaseModel):
    id: int
    tier_name: str
    min_amount: float
    max_amount: Optional[float]
    auto_approve: bool
    processing_time_hours: int
    requires_pin: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Account Rejection Schemas
class AccountRejectionCreate(BaseModel):
    user_id: int
    rejection_reason: str
    rejection_details: Optional[str] = None
    can_appeal: bool = True

class AccountRejectionResponse(BaseModel):
    id: int
    user_id: int
    rejection_reason: str
    rejection_details: Optional[str]
    rejected_by: Optional[int]
    can_appeal: bool
    appeal_deadline: Optional[datetime]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Notification Trigger Schemas
class NotificationTriggerCreate(BaseModel):
    event_type: str
    trigger_name: str
    email_template: str
    send_email: bool = True
    send_in_app: bool = True
    priority: str = "normal"
    retry_on_failure: bool = True
    max_retries: int = 3

class NotificationTriggerResponse(BaseModel):
    id: int
    event_type: str
    trigger_name: str
    send_email: bool
    send_in_app: bool
    priority: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Transaction History Schemas
class TransactionHistoryResponse(BaseModel):
    id: int
    user_id: int
    wallet_id: Optional[int]
    tx_type: str
    amount: float
    currency: str
    status: str
    blockchain_hash: Optional[str]
    block_explorer_url: Optional[str]
    from_address: Optional[str]
    to_address: Optional[str]
    fee: float
    description: Optional[str]
    created_at: datetime
    confirmed_at: Optional[datetime]

    class Config:
        from_attributes = True

# Card Management Schemas
class CardManagementResponse(BaseModel):
    id: int
    card_id: str
    user_id: int
    is_frozen: bool
    freeze_reason: Optional[str]
    spend_limit: Optional[float]
    spend_limit_period: str
    transaction_count: int
    total_spent: float
    last_used_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class CardFreezeRequest(BaseModel):
    card_id: str
    reason: str

class CardLimitUpdateRequest(BaseModel):
    card_id: str
    spend_limit: float
    period: str = "monthly"

# Notification Schemas
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    event_type: str
    title: str
    message: str
    email_sent: bool
    in_app_sent: bool
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True
