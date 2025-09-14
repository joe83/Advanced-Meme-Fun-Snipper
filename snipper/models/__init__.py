"""Trade data models and Pydantic schemas."""

import time
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TradeStatus(str, Enum):
    """Trade status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"
    FAILED = "failed"


class TradeSide(str, Enum):
    """Trade side enumeration."""
    BUY = "buy"
    SELL = "sell"


class CloseReason(str, Enum):
    """Trade close reason enumeration."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    TIME_EXIT = "time_exit"
    MANUAL = "manual"
    ERROR = "error"


class SwapEvent(BaseModel):
    """Individual swap event within a trade."""
    timestamp: float = Field(default_factory=time.time)
    side: TradeSide
    token_mint: str
    amount: int
    tx_signature: Optional[str] = None
    latency_ms: Optional[float] = None
    fee_sol: Optional[float] = None
    jito_tip_sol: Optional[float] = None
    error: Optional[str] = None


class Trade(BaseModel):
    """Complete trade record with lifecycle events."""
    
    # Identity
    trade_id: str
    created_at: float = Field(default_factory=time.time)
    
    # Token info
    token_mint: str
    token_name: Optional[str] = None
    
    # Analysis
    analysis_text: Optional[str] = None
    analysis_score: Optional[float] = None
    
    # Entry
    entry_price: Optional[float] = None
    buy_amount_sol: float
    entry_timestamp: Optional[float] = None
    
    # Position tracking
    peak_price: Optional[float] = None
    trailing_stop_price: Optional[float] = None
    current_price: Optional[float] = None
    
    # Exit
    exit_price: Optional[float] = None
    exit_timestamp: Optional[float] = None
    close_reason: Optional[CloseReason] = None
    
    # Performance
    pnl_percent: Optional[float] = None
    hold_time_minutes: Optional[float] = None
    total_fees_sol: float = 0.0
    
    # Status
    status: TradeStatus = TradeStatus.PENDING
    
    # Events
    swaps: list[SwapEvent] = Field(default_factory=list)
    
    # Metadata
    liquidity_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    correlation_id: Optional[str] = None
    
    def add_swap_event(self, swap: SwapEvent) -> None:
        """Add a swap event to the trade."""
        self.swaps.append(swap)
        
        # Update fees
        if swap.fee_sol:
            self.total_fees_sol += swap.fee_sol
        if swap.jito_tip_sol:
            self.total_fees_sol += swap.jito_tip_sol
    
    def calculate_pnl(self) -> Optional[float]:
        """Calculate current PnL percentage."""
        if self.entry_price and self.current_price:
            self.pnl_percent = ((self.current_price - self.entry_price) / self.entry_price) * 100
        return self.pnl_percent
    
    def calculate_hold_time(self) -> Optional[float]:
        """Calculate hold time in minutes."""
        if self.entry_timestamp:
            end_time = self.exit_timestamp or time.time()
            self.hold_time_minutes = (end_time - self.entry_timestamp) / 60
        return self.hold_time_minutes
    
    def update_peak_price(self, price: float) -> None:
        """Update peak price if new price is higher."""
        if self.peak_price is None or price > self.peak_price:
            self.peak_price = price
    
    def close_trade(self, exit_price: float, reason: CloseReason) -> None:
        """Close the trade with final details."""
        self.exit_price = exit_price
        self.exit_timestamp = time.time()
        self.close_reason = reason
        self.status = TradeStatus.CLOSED
        self.current_price = exit_price
        self.calculate_pnl()
        self.calculate_hold_time()
    
    def to_mongo_dict(self) -> dict:
        """Convert to dictionary for MongoDB storage."""
        data = self.model_dump()
        # Convert datetime fields for MongoDB
        data['created_at_datetime'] = datetime.fromtimestamp(self.created_at)
        if self.entry_timestamp:
            data['entry_datetime'] = datetime.fromtimestamp(self.entry_timestamp)
        if self.exit_timestamp:
            data['exit_datetime'] = datetime.fromtimestamp(self.exit_timestamp)
        return data
    
    @classmethod
    def from_mongo_dict(cls, data: dict) -> 'Trade':
        """Create Trade instance from MongoDB document."""
        # Remove datetime fields that we don't need for reconstruction
        data.pop('created_at_datetime', None)
        data.pop('entry_datetime', None)
        data.pop('exit_datetime', None)
        return cls(**data)


class TradeFilter(BaseModel):
    """Filter criteria for querying trades."""
    status: Optional[TradeStatus] = None
    token_mint: Optional[str] = None
    min_pnl_percent: Optional[float] = None
    max_pnl_percent: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    close_reason: Optional[CloseReason] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class TradeStats(BaseModel):
    """Trade statistics summary."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl_percent: float
    avg_hold_time_minutes: float
    total_fees_sol: float
    best_trade_pnl: Optional[float] = None
    worst_trade_pnl: Optional[float] = None