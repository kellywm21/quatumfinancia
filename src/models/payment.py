from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean
from datetime import datetime
from src.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
