"""Tests for risk management components."""

import time
import pytest

from snipper.risk.guards import CircuitBreaker, DailySpendTracker, SlippageGuard, RiskManager


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(max_failures=3, cooldown_minutes=5)
        
        assert cb.max_failures == 3
        assert cb.cooldown_minutes == 5
        assert cb.failure_count == 0
        assert cb.is_open is False
        assert cb.can_trade() is True
    
    def test_failure_recording(self):
        """Test failure recording and circuit opening."""
        cb = CircuitBreaker(max_failures=2, cooldown_minutes=5)
        
        # Record first failure
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.is_open is False
        assert cb.can_trade() is True
        
        # Record second failure - should open circuit
        cb.record_failure()
        assert cb.failure_count == 2
        assert cb.is_open is True
        assert cb.can_trade() is False
    
    def test_success_recording(self):
        """Test success recording and circuit reset."""
        cb = CircuitBreaker(max_failures=2, cooldown_minutes=5)
        
        # Record failure then success
        cb.record_failure()
        cb.record_success()
        
        assert cb.failure_count == 0
        assert cb.is_open is False
        assert cb.can_trade() is True
    
    def test_cooldown_period(self):
        """Test cooldown period functionality."""
        cb = CircuitBreaker(max_failures=1, cooldown_minutes=0.01)  # 0.6 seconds
        
        # Open circuit
        cb.record_failure()
        assert cb.can_trade() is False
        
        # Wait for cooldown
        time.sleep(0.02)  # 1.2 seconds
        assert cb.can_trade() is True
        assert cb.is_open is False


class TestDailySpendTracker:
    """Test DailySpendTracker functionality."""
    
    def test_spend_tracker_initialization(self):
        """Test spend tracker initialization."""
        tracker = DailySpendTracker(daily_limit=1.0)
        
        assert tracker.daily_limit == 1.0
        assert tracker.get_daily_spent() == 0.0
        assert tracker.can_spend(0.5) is True
    
    def test_spend_recording(self):
        """Test spend recording functionality."""
        tracker = DailySpendTracker(daily_limit=1.0)
        
        # Record spend
        tracker.record_spend(0.3)
        assert tracker.get_daily_spent() == 0.3
        assert tracker.can_spend(0.5) is True
        assert tracker.can_spend(0.8) is False
        
        # Record another spend
        tracker.record_spend(0.4)
        assert tracker.get_daily_spent() == 0.7
        assert tracker.can_spend(0.2) is True
        assert tracker.can_spend(0.4) is False
    
    def test_daily_limit_enforcement(self):
        """Test daily limit enforcement."""
        tracker = DailySpendTracker(daily_limit=1.0)
        
        # Spend up to limit
        tracker.record_spend(1.0)
        assert tracker.can_spend(0.01) is False
        
        # Check status
        status = tracker.get_status()
        assert status['daily_spent'] == 1.0
        assert status['remaining'] == 0.0
        assert status['utilization_percent'] == 100.0


class TestSlippageGuard:
    """Test SlippageGuard functionality."""
    
    def test_slippage_guard_initialization(self):
        """Test slippage guard initialization."""
        guard = SlippageGuard(max_slippage_percent=5.0)
        assert guard.max_slippage_percent == 5.0
    
    def test_acceptable_slippage(self):
        """Test acceptable slippage detection."""
        guard = SlippageGuard(max_slippage_percent=5.0)
        
        # No slippage
        assert guard.check_slippage(1.0, 1.0) is True
        
        # Small slippage (2%)
        assert guard.check_slippage(1.0, 0.98) is True
        assert guard.check_slippage(1.0, 1.02) is True
        
        # Acceptable slippage (5%)
        assert guard.check_slippage(1.0, 0.95) is True
        assert guard.check_slippage(1.0, 1.05) is True
    
    def test_excessive_slippage(self):
        """Test excessive slippage detection."""
        guard = SlippageGuard(max_slippage_percent=5.0)
        
        # Excessive slippage (6%)
        assert guard.check_slippage(1.0, 0.94) is False
        assert guard.check_slippage(1.0, 1.06) is False
        
        # Very high slippage (10%)
        assert guard.check_slippage(1.0, 0.90) is False
        assert guard.check_slippage(1.0, 1.10) is False
    
    def test_invalid_expected_price(self):
        """Test handling of invalid expected price."""
        guard = SlippageGuard(max_slippage_percent=5.0)
        
        # Zero or negative expected price
        assert guard.check_slippage(0, 1.0) is False
        assert guard.check_slippage(-1.0, 1.0) is False


class TestRiskManager:
    """Test RiskManager integration."""
    
    def test_risk_manager_can_trade(self, mock_settings):
        """Test risk manager trade authorization."""
        # Create risk manager with test settings
        from snipper.risk.guards import RiskManager
        import snipper.config
        
        # Temporarily override settings for test
        original_settings = snipper.config.settings
        snipper.config.settings = mock_settings
        
        try:
            risk_manager = RiskManager()
            
            # Valid trade amount
            can_trade, reason = risk_manager.can_trade(0.005)
            assert can_trade is True
            assert reason == "OK"
            
            # Invalid trade amount (zero)
            can_trade, reason = risk_manager.can_trade(0)
            assert can_trade is False
            assert "Invalid trade amount" in reason
            
            # Excessive trade amount
            can_trade, reason = risk_manager.can_trade(1.0)
            assert can_trade is False
            assert "exceeds maximum" in reason
            
        finally:
            snipper.config.settings = original_settings
    
    def test_risk_manager_trade_recording(self, mock_settings):
        """Test risk manager trade recording."""
        from snipper.risk.guards import RiskManager
        import snipper.config
        
        # Temporarily override settings for test
        original_settings = snipper.config.settings
        snipper.config.settings = mock_settings
        
        try:
            risk_manager = RiskManager()
            
            # Record successful trade
            risk_manager.record_trade_success(0.01)
            assert risk_manager.spend_tracker.get_daily_spent() == 0.01
            assert risk_manager.circuit_breaker.failure_count == 0
            
            # Record failed trade
            risk_manager.record_trade_failure("test_error")
            assert risk_manager.circuit_breaker.failure_count == 1
            
        finally:
            snipper.config.settings = original_settings
    
    def test_risk_manager_status(self, mock_settings):
        """Test risk manager status reporting."""
        from snipper.risk.guards import RiskManager
        import snipper.config
        
        # Temporarily override settings for test
        original_settings = snipper.config.settings
        snipper.config.settings = mock_settings
        
        try:
            risk_manager = RiskManager()
            
            status = risk_manager.get_status()
            
            assert 'circuit_breaker' in status
            assert 'spending' in status
            assert 'slippage_guard' in status
            
            assert status['circuit_breaker']['can_trade'] is True
            assert status['spending']['daily_limit'] == 1.0
            assert status['slippage_guard']['max_slippage_percent'] == 5.0
            
        finally:
            snipper.config.settings = original_settings