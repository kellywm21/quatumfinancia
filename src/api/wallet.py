import secrets
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from cryptography.fernet import Fernet
from src.database import get_db
from src.models.payment import (
    User, Wallet, WalletBalance, WalletAddress, CryptoTransaction,
    InternalTransfer, CryptoSettings, TransactionPin
)
from src.schemas.payment import (
    WalletResponse, WalletBalanceResponse, WalletAddressResponse,
    CryptoTransactionResponse, InternalTransferCreate, InternalTransferResponse,
    CryptoSettingsResponse, SendCryptoRequest, WalletOverviewResponse
)
from src.services.auth_service import get_current_active_user, verify_password
from src.services.email_service import email_service

router = APIRouter(prefix="/api/wallet", tags=["wallet"])

# Encryption key for wallet seeds (in production, this should be from environment)
ENCRYPTION_KEY = Fernet.generate_key()
cipher = Fernet(ENCRYPTION_KEY)

def generate_wallet_id() -> str:
    """Generate a unique wallet identifier"""
    return f"wallet_{secrets.token_hex(16)}"

def encrypt_seed(seed: str) -> str:
    """Encrypt wallet seed"""
    return cipher.encrypt(seed.encode()).decode()

def decrypt_seed(encrypted_seed: str) -> str:
    """Decrypt wallet seed"""
    return cipher.decrypt(encrypted_seed.encode()).decode()

def generate_address(currency: str, derivation_path: str) -> str:
    """Generate a crypto address (simplified - in production use proper crypto libraries)"""
    # This is a simplified implementation. In production, you'd use:
    # - bitcoinlib for BTC
    # - web3.py for ETH
    # - etc.
    import hashlib

    if currency == "BTC":
        # Simplified BTC address generation
        hash_input = f"{currency}_{derivation_path}_{secrets.token_hex(32)}"
        hash_obj = hashlib.sha256(hash_input.encode())
        # Add version byte (0x00 for mainnet) and checksum
        version_hash = b'\x00' + hash_obj.digest()[:20]
        checksum = hashlib.sha256(hashlib.sha256(version_hash).digest()).digest()[:4]
        raw = version_hash + checksum

        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        num = int.from_bytes(raw, byteorder="big")
        encoded = ""
        while num > 0:
            num, rem = divmod(num, 58)
            encoded = alphabet[rem] + encoded

        # Preserve leading zero bytes as '1's
        leading_zeros = len(raw) - len(raw.lstrip(b"\x00"))
        address = "1" * leading_zeros + encoded
        return address
    elif currency == "ETH":
        # Simplified ETH address generation
        hash_input = f"{currency}_{derivation_path}_{secrets.token_hex(32)}"
        keccak = hashlib.sha3_256(hash_input.encode())
        address = "0x" + keccak.hexdigest()[-40:]
        return address
    else:
        # Generic address for other currencies
        return f"{currency}_{secrets.token_hex(20)}"

@router.post("/create", response_model=WalletResponse)
def create_wallet(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new wallet for the user"""

    # Check if user already has a wallet
    existing_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a wallet"
        )

    # Generate wallet seed (simplified - in production use bip39)
    seed = secrets.token_hex(32)

    # Encrypt the seed
    encrypted_seed = encrypt_seed(seed)

    wallet = Wallet(
        user_id=current_user.id,
        wallet_id=generate_wallet_id(),
        encrypted_seed=encrypted_seed,
        status="active"
    )

    db.add(wallet)
    db.commit()
    db.refresh(wallet)

    # Create initial balances for supported currencies
    supported_currencies = ["BTC", "ETH", "USDC", "USDT"]
    for currency in supported_currencies:
        balance = WalletBalance(
            wallet_id=wallet.id,
            currency=currency,
            balance=0.0,
            available_balance=0.0,
            locked_balance=0.0
        )
        db.add(balance)

    # Create initial addresses for each currency
    for currency in supported_currencies:
        address = generate_address(currency, "m/44'/0'/0'/0/0")  # Standard derivation path
        wallet_address = WalletAddress(
            wallet_id=wallet.id,
            currency=currency,
            address=address,
            derivation_path="m/44'/0'/0'/0/0",
            label=f"{currency} Main Address",
            is_change=False
        )
        db.add(wallet_address)

    db.commit()

    return wallet

@router.get("/", response_model=WalletResponse)
def get_wallet(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's wallet"""

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found. Create one first."
        )

    return wallet

@router.get("/overview", response_model=WalletOverviewResponse)
def get_wallet_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get complete wallet overview"""

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    # Get balances
    balances = db.query(WalletBalance).filter(WalletBalance.wallet_id == wallet.id).all()

    # Get recent transactions (last 10)
    recent_transactions = db.query(CryptoTransaction).filter(
        CryptoTransaction.wallet_id == wallet.id
    ).order_by(desc(CryptoTransaction.created_at)).limit(10).all()

    # Calculate total value in USD (simplified - in production use price feeds)
    total_value_usd = sum(balance.balance * get_crypto_price(balance.currency) for balance in balances)

    return WalletOverviewResponse(
        wallet=wallet,
        balances=balances,
        recent_transactions=recent_transactions,
        total_value_usd=total_value_usd
    )

@router.get("/balances", response_model=list[WalletBalanceResponse])
def get_wallet_balances(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get wallet balances"""

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    balances = db.query(WalletBalance).filter(WalletBalance.wallet_id == wallet.id).all()
    return balances

@router.get("/addresses", response_model=list[WalletAddressResponse])
def get_wallet_addresses(
    currency: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get wallet addresses"""

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    query = db.query(WalletAddress).filter(WalletAddress.wallet_id == wallet.id)
    if currency:
        query = query.filter(WalletAddress.currency == currency)

    addresses = query.all()
    return addresses

@router.post("/addresses/generate")
def generate_new_address(
    currency: str,
    label: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate a new address for a specific currency"""

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    # Get the next derivation path (simplified)
    existing_count = db.query(WalletAddress).filter(
        and_(WalletAddress.wallet_id == wallet.id, WalletAddress.currency == currency)
    ).count()

    derivation_path = f"m/44'/0'/0'/0/{existing_count}"
    address = generate_address(currency, derivation_path)

    wallet_address = WalletAddress(
        wallet_id=wallet.id,
        currency=currency,
        address=address,
        derivation_path=derivation_path,
        label=label or f"{currency} Address {existing_count + 1}",
        is_change=False
    )

    db.add(wallet_address)
    db.commit()
    db.refresh(wallet_address)

    return wallet_address

@router.get("/transactions", response_model=list[CryptoTransactionResponse])
def get_transactions(
    currency: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get wallet transactions"""

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    query = db.query(CryptoTransaction).filter(CryptoTransaction.wallet_id == wallet.id)
    if currency:
        query = query.filter(CryptoTransaction.currency == currency)

    transactions = query.order_by(desc(CryptoTransaction.created_at)).offset(offset).limit(limit).all()
    return transactions

@router.post("/send", response_model=CryptoTransactionResponse)
def send_crypto(
    request: SendCryptoRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send cryptocurrency"""

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    # Verify transaction PIN if the user has one configured
    pin_record = db.query(TransactionPin).filter(TransactionPin.user_id == current_user.id).first()
    if pin_record:
        if not request.transaction_pin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction PIN is required for this account"
            )
        if not verify_password(request.transaction_pin, pin_record.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid transaction PIN"
            )

    # Check balance
    balance = db.query(WalletBalance).filter(
        and_(WalletBalance.wallet_id == wallet.id, WalletBalance.currency == request.currency)
    ).first()

    if not balance or balance.available_balance < request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance"
        )

    # Calculate fee (simplified)
    fee = calculate_fee(request.currency, request.fee_priority)

    if balance.available_balance < (request.amount + fee):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance including fees"
        )

    # Generate transaction hash (simplified)
    tx_hash = f"tx_{secrets.token_hex(16)}"

    # Create transaction record
    transaction = CryptoTransaction(
        wallet_id=wallet.id,
        tx_hash=tx_hash,
        currency=request.currency,
        tx_type="send",
        amount=request.amount,
        fee=fee,
        to_address=request.to_address,
        status="pending",
        memo=request.memo
    )

    # Update balance
    balance.available_balance -= (request.amount + fee)
    balance.locked_balance += (request.amount + fee)
    balance.updated_at = datetime.utcnow()

    db.add(transaction)
    db.add(balance)
    db.commit()
    db.refresh(transaction)

    # In production, this would broadcast to the blockchain
    # For demo, simulate potential failure
    import random
    if random.random() < 0.1:  # 10% chance of failure for demo
        transaction.status = "failed"
        transaction.error_message = "Network congestion - transaction failed"
        balance.available_balance += (request.amount + fee)  # Refund
        balance.locked_balance = 0
        
        db.add(transaction)
        db.add(balance)
        db.commit()
        
        # Send failure notification
        email_service.send_transaction_failed_email(
            current_user.email, 
            current_user.username, 
            request.amount, 
            request.currency,
            transaction.error_message
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction failed: {transaction.error_message}"
        )
    
    # Success case
    transaction.status = "confirmed"
    transaction.confirmed_at = datetime.utcnow()
    balance.balance = balance.available_balance + balance.locked_balance
    balance.locked_balance = 0

    db.add(transaction)
    db.add(balance)
    db.commit()

    # Send success notification
    email_service.send_transaction_success_email(
        current_user.email,
        current_user.username,
        request.amount,
        request.currency,
        tx_hash
    )

    return transaction

@router.post("/transfer/internal", response_model=InternalTransferResponse)
def internal_transfer(
    request: InternalTransferCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Transfer crypto internally between wallets"""

    # Get sender wallet
    from_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not from_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender wallet not found"
        )

    # Get receiver wallet
    to_wallet = db.query(Wallet).filter(Wallet.id == request.to_wallet_id).first()
    if not to_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver wallet not found"
        )

    # Check sender balance
    from_balance = db.query(WalletBalance).filter(
        and_(WalletBalance.wallet_id == from_wallet.id, WalletBalance.currency == request.currency)
    ).first()

    if not from_balance or from_balance.available_balance < request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance"
        )

    # Get or create receiver balance
    to_balance = db.query(WalletBalance).filter(
        and_(WalletBalance.wallet_id == to_wallet.id, WalletBalance.currency == request.currency)
    ).first()

    if not to_balance:
        to_balance = WalletBalance(
            wallet_id=to_wallet.id,
            currency=request.currency,
            balance=0.0,
            available_balance=0.0,
            locked_balance=0.0
        )
        db.add(to_balance)

    # Create internal transfer record
    transfer = InternalTransfer(
        from_wallet_id=from_wallet.id,
        to_wallet_id=to_wallet.id,
        currency=request.currency,
        amount=request.amount,
        fee=0.0,  # No fees for internal transfers
        status="pending",
        memo=request.memo
    )

    # Update balances
    from_balance.available_balance -= request.amount
    to_balance.available_balance += request.amount
    to_balance.balance += request.amount

    from_balance.updated_at = datetime.utcnow()
    to_balance.updated_at = datetime.utcnow()

    db.add(transfer)
    db.add(from_balance)
    db.add(to_balance)
    db.commit()
    db.refresh(transfer)

    # Mark as completed (internal transfers are instant)
    transfer.status = "completed"
    transfer.completed_at = datetime.utcnow()

    db.add(transfer)
    db.commit()

    return transfer

@router.get("/settings", response_model=list[CryptoSettingsResponse])
def get_crypto_settings():
    """Get supported cryptocurrency settings"""
    # In production, this would come from database
    # For demo, return hardcoded settings
    settings = [
        CryptoSettingsResponse(
            id=1, currency="BTC", name="Bitcoin", symbol="BTC", decimals=8,
            network="mainnet", min_confirmations=1, is_active=True
        ),
        CryptoSettingsResponse(
            id=2, currency="ETH", name="Ethereum", symbol="ETH", decimals=18,
            network="mainnet", min_confirmations=12, is_active=True
        ),
        CryptoSettingsResponse(
            id=3, currency="USDC", name="USD Coin", symbol="USDC", decimals=6,
            contract_address="0xA0b86a33E6441e88C5F2712C3E9b74F5b6b6b6b6",
            network="mainnet", min_confirmations=12, is_active=True
        ),
        CryptoSettingsResponse(
            id=4, currency="USDT", name="Tether", symbol="USDT", decimals=6,
            contract_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
            network="mainnet", min_confirmations=12, is_active=True
        )
    ]
    return settings

def calculate_fee(currency: str, priority: str) -> float:
    """Calculate transaction fee based on currency and priority"""
    base_fees = {
        "BTC": 0.0001,
        "ETH": 0.001,
        "USDC": 0.001,
        "USDT": 0.001
    }

    multipliers = {
        "low": 0.5,
        "normal": 1.0,
        "high": 2.0
    }

    return base_fees.get(currency, 0.001) * multipliers.get(priority, 1.0)

def get_crypto_price(currency: str) -> float:
    """Get cryptocurrency price in USD (simplified - in production use price feeds)"""
    # Mock prices - in production use CoinGecko, CoinMarketCap, etc.
    prices = {
        "BTC": 45000.0,
        "ETH": 3000.0,
        "USDC": 1.0,
        "USDT": 1.0
    }
    return prices.get(currency, 0.0)