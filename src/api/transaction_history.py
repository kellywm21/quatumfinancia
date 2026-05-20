from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from src.database import get_db
from src.models.payment import User, TransactionHistory
from src.schemas.payment import TransactionHistoryResponse
from src.services.auth_service import get_current_active_user, get_current_admin_user

router = APIRouter(prefix="/api/transaction-history", tags=["transaction-history"])

# Block explorer mappings
BLOCK_EXPLORERS = {
    "BTC": "https://blockchain.com/btc/tx/",
    "ETH": "https://etherscan.io/tx/",
    "USDC": "https://etherscan.io/tx/",
    "USDT": "https://etherscan.io/tx/",
    "MATIC": "https://polygonscan.com/tx/"
}

def generate_block_explorer_url(currency: str, tx_hash: str) -> str:
    """Generate block explorer URL for a transaction"""
    base_url = BLOCK_EXPLORERS.get(currency)
    if base_url and tx_hash:
        return base_url + tx_hash
    return None

@router.get("/user", response_model=list[TransactionHistoryResponse])
def get_user_transaction_history(
    limit: int = 100,
    offset: int = 0,
    tx_type: str = None,
    currency: str = None,
    status_filter: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transaction history for current user with filters"""
    
    query = db.query(TransactionHistory).filter(
        TransactionHistory.user_id == current_user.id
    )
    
    if tx_type:
        query = query.filter(TransactionHistory.tx_type == tx_type)
    
    if currency:
        query = query.filter(TransactionHistory.currency == currency)
    
    if status_filter:
        query = query.filter(TransactionHistory.status == status_filter)
    
    if start_date:
        query = query.filter(TransactionHistory.created_at >= start_date)
    
    if end_date:
        query = query.filter(TransactionHistory.created_at <= end_date)
    
    transactions = query.order_by(
        desc(TransactionHistory.created_at)
    ).offset(offset).limit(limit).all()
    
    return transactions

@router.get("/user/{tx_id}", response_model=TransactionHistoryResponse)
def get_transaction_details(
    tx_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed transaction information with block explorer link"""
    
    transaction = db.query(TransactionHistory).filter(
        and_(
            TransactionHistory.id == tx_id,
            TransactionHistory.user_id == current_user.id
        )
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction

@router.get("/explore/{tx_id}")
def get_block_explorer_link(
    tx_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get block explorer link for a transaction"""
    
    transaction = db.query(TransactionHistory).filter(
        and_(
            TransactionHistory.id == tx_id,
            TransactionHistory.user_id == current_user.id
        )
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    if not transaction.blockchain_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This transaction is not on the blockchain"
        )
    
    explorer_url = generate_block_explorer_url(
        transaction.currency,
        transaction.blockchain_hash
    )
    
    if not explorer_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No block explorer available for {transaction.currency}"
        )
    
    return {
        "currency": transaction.currency,
        "tx_hash": transaction.blockchain_hash,
        "explorer_url": explorer_url,
        "block_height": transaction.block_height,
        "confirmations": transaction.confirmations,
        "status": transaction.status
    }

@router.get("/summary")
def get_transaction_summary(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transaction summary for a user over a period"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    transactions = db.query(TransactionHistory).filter(
        and_(
            TransactionHistory.user_id == current_user.id,
            TransactionHistory.created_at >= start_date
        )
    ).all()
    
    # Calculate statistics
    total_received = 0.0
    total_sent = 0.0
    total_fees = 0.0
    transaction_counts = {
        "deposit": 0,
        "withdrawal": 0,
        "transfer": 0,
        "card_transaction": 0,
        "card_fund": 0
    }
    status_counts = {
        "pending": 0,
        "confirmed": 0,
        "failed": 0
    }
    
    by_currency = {}
    
    for tx in transactions:
        # Count by type
        if tx.tx_type in transaction_counts:
            transaction_counts[tx.tx_type] += 1
        
        # Count by status
        if tx.status in status_counts:
            status_counts[tx.status] += 1
        
        # Count by currency
        if tx.currency not in by_currency:
            by_currency[tx.currency] = {
                "total_amount": 0.0,
                "total_fees": 0.0,
                "transaction_count": 0
            }
        
        by_currency[tx.currency]["total_amount"] += tx.amount
        by_currency[tx.currency]["total_fees"] += tx.fee
        by_currency[tx.currency]["transaction_count"] += 1
        
        # Categorize sent/received
        if tx.tx_type in ["withdrawal", "transfer", "card_transaction"]:
            total_sent += tx.amount
        elif tx.tx_type in ["deposit", "card_fund"]:
            total_received += tx.amount
        
        total_fees += tx.fee
    
    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "total_transactions": len(transactions),
        "total_received": total_received,
        "total_sent": total_sent,
        "total_fees": total_fees,
        "net_activity": total_received - total_sent,
        "transaction_counts": transaction_counts,
        "status_counts": status_counts,
        "by_currency": by_currency
    }

@router.get("/export/csv")
def export_transaction_csv(
    start_date: datetime = None,
    end_date: datetime = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export transaction history as CSV"""
    
    query = db.query(TransactionHistory).filter(
        TransactionHistory.user_id == current_user.id
    )
    
    if start_date:
        query = query.filter(TransactionHistory.created_at >= start_date)
    
    if end_date:
        query = query.filter(TransactionHistory.created_at <= end_date)
    
    transactions = query.order_by(
        desc(TransactionHistory.created_at)
    ).all()
    
    # Build CSV content
    csv_lines = [
        "Date,Type,Amount,Currency,Status,Fee,From,To,Hash,Block Explorer URL"
    ]
    
    for tx in transactions:
        explorer_url = generate_block_explorer_url(tx.currency, tx.blockchain_hash) if tx.blockchain_hash else ""
        csv_lines.append(
            f"{tx.created_at.isoformat()},{tx.tx_type},{tx.amount},{tx.currency},"
            f"{tx.status},{tx.fee},{tx.from_address or ''},{tx.to_address or ''},"
            f"{tx.blockchain_hash or ''},{explorer_url}"
        )
    
    return {
        "filename": f"advancia_transactions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
        "content": "\n".join(csv_lines),
        "transaction_count": len(transactions)
    }

@router.post("/create")
def record_transaction(
    tx_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Record a new transaction in history"""
    
    transaction = TransactionHistory(
        user_id=current_user.id,
        wallet_id=tx_data.get("wallet_id"),
        tx_type=tx_data.get("tx_type"),
        amount=tx_data.get("amount"),
        currency=tx_data.get("currency"),
        status=tx_data.get("status", "pending"),
        blockchain_hash=tx_data.get("blockchain_hash"),
        from_address=tx_data.get("from_address"),
        to_address=tx_data.get("to_address"),
        fee=tx_data.get("fee", 0.0),
        description=tx_data.get("description"),
        metadata=tx_data.get("tx_metadata")
    )
    
    # Generate block explorer URL if hash is provided
    if transaction.blockchain_hash:
        transaction.block_explorer_url = generate_block_explorer_url(
            transaction.currency,
            transaction.blockchain_hash
        )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    return transaction
