"""Risk management guards and circuit breakers."""

import time
from typing import Dict, Optional

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """Circuit breaker to halt trading after consecutive failures."""
    
    def __init__(self, max_failures: int, cooldown_minutes: int):
        self.max_failures = max_failures
        self.cooldown_minutes = cooldown_minutes
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.is_open = False
        
        logger.info(
            "Circuit breaker initialized",
            extra={
                'max_failures': max_failures,
                'cooldown_minutes': cooldown_minutes,
                'event': 'circuit_breaker_initialized'
            }
        )
    
    def record_failure(self) -> None:
        """Record a failure and update circuit breaker state."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.max_failures:
            self.is_open = True
            logger.warning(
                "Circuit breaker opened",
                extra={
                    'failure_count': self.failure_count,
                    'max_failures': self.max_failures,
                    'event': 'circuit_breaker_opened'
                }
            )
    
    def record_success(self) -> None:
        """Record a success and reset failure count."""
        if self.failure_count > 0:
            logger.info(
                "Circuit breaker reset after success",
                extra={
                    'previous_failure_count': self.failure_count,
                    'event': 'circuit_breaker_reset'
                }
            )
        
        self.failure_count = 0
        self.is_open = False
    
    def can_trade(self) -> bool:
        """Check if trading is allowed."""
        if not self.is_open:
            return True
        
        if self.last_failure_time is None:
            return True
        
        # Check if cooldown period has passed
        elapsed_minutes = (time.time() - self.last_failure_time) / 60
        if elapsed_minutes >= self.cooldown_minutes:
            logger.info(
                "Circuit breaker cooldown expired, allowing trading",
                extra={
                    'elapsed_minutes': elapsed_minutes,
                    'cooldown_minutes': self.cooldown_minutes,
                    'event': 'circuit_breaker_cooldown_expired'
                }
            )
            self.is_open = False
            self.failure_count = 0
            return True
        
        return False
    
    def get_status(self) -> dict:
        """Get circuit breaker status."""
        remaining_cooldown = 0
        if self.is_open and self.last_failure_time:
            elapsed_minutes = (time.time() - self.last_failure_time) / 60
            remaining_cooldown = max(0, self.cooldown_minutes - elapsed_minutes)
        
        return {
            'is_open': self.is_open,
            'failure_count': self.failure_count,
            'max_failures': self.max_failures,
            'remaining_cooldown_minutes': remaining_cooldown,
            'can_trade': self.can_trade()
        }


class DailySpendTracker:
    """Track daily SOL spending to enforce limits."""
    
    def __init__(self, daily_limit: float):
        self.daily_limit = daily_limit
        self.daily_spending: Dict[str, float] = {}  # date -> spent amount
        
        logger.info(
            "Daily spend tracker initialized",
            extra={
                'daily_limit': daily_limit,
                'event': 'spend_tracker_initialized'
            }
        )
    
    def _get_current_date(self) -> str:
        """Get current date string for tracking."""
        return time.strftime("%Y-%m-%d")
    
    def get_daily_spent(self) -> float:
        """Get amount spent today."""
        today = self._get_current_date()
        return self.daily_spending.get(today, 0.0)
    
    def can_spend(self, amount: float) -> bool:
        """Check if we can spend the given amount today."""
        daily_spent = self.get_daily_spent()
        return (daily_spent + amount) <= self.daily_limit
    
    def record_spend(self, amount: float) -> None:
        """Record a spend transaction."""
        today = self._get_current_date()
        current_spent = self.daily_spending.get(today, 0.0)
        new_total = current_spent + amount
        
        self.daily_spending[today] = new_total
        
        logger.info(
            "Spend recorded",
            extra={
                'amount': amount,
                'daily_total': new_total,
                'daily_limit': self.daily_limit,
                'remaining': self.daily_limit - new_total,
                'event': 'spend_recorded'
            }
        )
        
        # Clean up old entries (keep last 7 days)
        self._cleanup_old_entries()
    
    def _cleanup_old_entries(self) -> None:
        """Remove entries older than 7 days."""
        cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 days ago
        cutoff_date = time.strftime("%Y-%m-%d", time.localtime(cutoff_time))
        
        dates_to_remove = [date for date in self.daily_spending.keys() if date < cutoff_date]
        for date in dates_to_remove:
            del self.daily_spending[date]
    
    def get_status(self) -> dict:
        """Get spending status."""
        daily_spent = self.get_daily_spent()
        return {
            'daily_limit': self.daily_limit,
            'daily_spent': daily_spent,
            'remaining': self.daily_limit - daily_spent,
            'utilization_percent': (daily_spent / self.daily_limit) * 100 if self.daily_limit > 0 else 0
        }


class SlippageGuard:
    """Guard against excessive slippage."""
    
    def __init__(self, max_slippage_percent: float):
        self.max_slippage_percent = max_slippage_percent
        
        logger.info(
            "Slippage guard initialized",
            extra={
                'max_slippage_percent': max_slippage_percent,
                'event': 'slippage_guard_initialized'
            }
        )
    
    def check_slippage(self, expected_price: float, actual_price: float) -> bool:
        """
        Check if slippage is within acceptable limits.
        
        Returns:
            True if slippage is acceptable, False otherwise
        """
        if expected_price <= 0:
            logger.warning(
                "Invalid expected price for slippage check",
                extra={
                    'expected_price': expected_price,
                    'event': 'invalid_expected_price'
                }
            )
            return False
        
        slippage_percent = abs((actual_price - expected_price) / expected_price) * 100
        is_acceptable = slippage_percent <= self.max_slippage_percent
        
        logger.info(
            "Slippage check performed",
            extra={
                'expected_price': expected_price,
                'actual_price': actual_price,
                'slippage_percent': slippage_percent,
                'max_slippage_percent': self.max_slippage_percent,
                'is_acceptable': is_acceptable,
                'event': 'slippage_checked'
            }
        )
        
        return is_acceptable


class RiskManager:
    """Centralized risk management system."""
    
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            max_failures=settings.risk.max_consecutive_failures,
            cooldown_minutes=settings.risk.circuit_breaker_cooldown_min
        )
        
        self.spend_tracker = DailySpendTracker(
            daily_limit=settings.risk.daily_sol_limit
        )
        
        self.slippage_guard = SlippageGuard(
            max_slippage_percent=settings.risk.max_slippage_percent
        )
        
        logger.info(
            "Risk manager initialized",
            extra={
                'max_consecutive_failures': settings.risk.max_consecutive_failures,
                'daily_sol_limit': settings.risk.daily_sol_limit,
                'max_slippage_percent': settings.risk.max_slippage_percent,
                'event': 'risk_manager_initialized'
            }
        )
    
    def can_trade(self, amount_sol: float) -> tuple[bool, str]:
        """
        Check if trading is allowed.
        
        Returns:
            Tuple of (can_trade, reason)
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_trade():
            return False, "Circuit breaker is open"
        
        # Check daily spending limit
        if not self.spend_tracker.can_spend(amount_sol):
            daily_spent = self.spend_tracker.get_daily_spent()
            return False, f"Daily spend limit exceeded ({daily_spent:.4f}/{self.spend_tracker.daily_limit} SOL)"
        
        # Basic amount validation
        if amount_sol <= 0:
            return False, "Invalid trade amount"
        
        if amount_sol > settings.trading.buy_amount_sol * 2:  # Sanity check
            return False, "Trade amount exceeds maximum allowed"
        
        return True, "OK"
    
    def record_trade_success(self, amount_sol: float) -> None:
        """Record a successful trade."""
        self.circuit_breaker.record_success()
        self.spend_tracker.record_spend(amount_sol)
        
        logger.info(
            "Trade success recorded",
            extra={
                'amount_sol': amount_sol,
                'event': 'trade_success_recorded'
            }
        )
    
    def record_trade_failure(self, error_type: str) -> None:
        """Record a failed trade."""
        self.circuit_breaker.record_failure()
        
        logger.warning(
            "Trade failure recorded",
            extra={
                'error_type': error_type,
                'failure_count': self.circuit_breaker.failure_count,
                'event': 'trade_failure_recorded'
            }
        )
    
    def check_slippage(self, expected_price: float, actual_price: float) -> bool:
        """Check if slippage is acceptable."""
        return self.slippage_guard.check_slippage(expected_price, actual_price)
    
    def get_status(self) -> dict:
        """Get comprehensive risk management status."""
        return {
            'circuit_breaker': self.circuit_breaker.get_status(),
            'spending': self.spend_tracker.get_status(),
            'slippage_guard': {
                'max_slippage_percent': self.slippage_guard.max_slippage_percent
            }
        }


# Global risk manager instance
risk_manager = RiskManager()


def can_trade(amount_sol: float) -> tuple[bool, str]:
    """Check if trading is allowed."""
    return risk_manager.can_trade(amount_sol)


def record_trade_success(amount_sol: float) -> None:
    """Record a successful trade."""
    risk_manager.record_trade_success(amount_sol)


def record_trade_failure(error_type: str) -> None:
    """Record a failed trade."""
    risk_manager.record_trade_failure(error_type)


def check_slippage(expected_price: float, actual_price: float) -> bool:
    """Check if slippage is acceptable."""
    return risk_manager.check_slippage(expected_price, actual_price)


def get_risk_status() -> dict:
    """Get risk management status."""
    return risk_manager.get_status()