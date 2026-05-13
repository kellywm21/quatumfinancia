from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

# Authentication Schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

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
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

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
    account_token: str
    card_type: str = "VIRTUAL"
    spend_limit: float = 15000000  # $150,000 in cents
    spend_limit_duration: str = "MONTHLY"
    memo: Optional[str] = None

class CardFund(BaseModel):
    card_token: str
    amount: float = Field(..., gt=0)  # In cents
    memo: Optional[str] = None

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
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
