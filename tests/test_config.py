"""Tests for configuration validation."""

import pytest
from pydantic import ValidationError

from snipper.config import Settings, TradingConfig, RiskConfig


class TestTradingConfig:
    """Test TradingConfig validation."""
    
    def test_valid_trading_config(self):
        """Test valid trading configuration."""
        config = TradingConfig(
            buy_amount_sol=0.1,
            min_liquidity_usd=5000,
            min_market_cap_usd=10000,
            take_profit_multiplier=2.0,
            stop_loss_multiplier=0.7,
            trailing_stop_percent=10.0,
            max_hold_time_min=30,
            price_check_interval_sec=10,
            slippage_bps=50,
            jito_base_tip=100_000
        )
        
        assert config.buy_amount_sol == 0.1
        assert config.take_profit_multiplier == 2.0
    
    def test_invalid_buy_amount(self):
        """Test invalid buy amount validation."""
        with pytest.raises(ValidationError):
            TradingConfig(buy_amount_sol=0)  # Must be > 0
        
        with pytest.raises(ValidationError):
            TradingConfig(buy_amount_sol=11)  # Must be <= 10
    
    def test_invalid_multipliers(self):
        """Test invalid multiplier validation."""
        with pytest.raises(ValidationError):
            TradingConfig(take_profit_multiplier=0.5)  # Must be > 1.0
        
        with pytest.raises(ValidationError):
            TradingConfig(stop_loss_multiplier=1.1)  # Must be < 1.0


class TestRiskConfig:
    """Test RiskConfig validation."""
    
    def test_valid_risk_config(self):
        """Test valid risk configuration."""
        config = RiskConfig(
            daily_sol_limit=1.0,
            max_consecutive_failures=5,
            circuit_breaker_cooldown_min=60,
            max_slippage_percent=5.0
        )
        
        assert config.daily_sol_limit == 1.0
        assert config.max_consecutive_failures == 5
    
    def test_invalid_limits(self):
        """Test invalid limit validation."""
        with pytest.raises(ValidationError):
            RiskConfig(daily_sol_limit=0)  # Must be > 0
        
        with pytest.raises(ValidationError):
            RiskConfig(max_consecutive_failures=0)  # Must be >= 1


class TestSettings:
    """Test main Settings validation."""
    
    def test_solana_rpc_validation(self):
        """Test Solana RPC URL validation."""
        # Valid URLs
        settings = Settings(
            solana_rpc="https://api.mainnet-beta.solana.com",
            private_key="5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXp4c6afB5wuF" * 2,
            xai_api_key="test_key",
            birdeye_api_key="test_key"
        )
        assert settings.solana_rpc.startswith("https://")
        
        # Invalid URL
        with pytest.raises(ValidationError):
            Settings(
                solana_rpc="invalid_url",
                private_key="test_key",
                xai_api_key="test_key",
                birdeye_api_key="test_key"
            )
    
    def test_private_key_validation(self):
        """Test private key validation."""
        # Too short key
        with pytest.raises(ValidationError):
            Settings(
                solana_rpc="https://api.mainnet-beta.solana.com",
                private_key="short_key",
                xai_api_key="test_key",
                birdeye_api_key="test_key"
            )
    
    def test_pubkey_validation(self):
        """Test public key validation."""
        # Invalid pump.fun program ID
        with pytest.raises(ValidationError):
            Settings(
                solana_rpc="https://api.mainnet-beta.solana.com",
                private_key="5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXp4c6afB5wuF" * 2,
                xai_api_key="test_key",
                birdeye_api_key="test_key",
                pump_fun_program_id="invalid_pubkey"
            )
    
    def test_nested_config_validation(self):
        """Test nested configuration validation."""
        settings = Settings(
            solana_rpc="https://api.mainnet-beta.solana.com",
            private_key="5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXp4c6afB5wuF" * 2,
            xai_api_key="test_key",
            birdeye_api_key="test_key",
            trading=TradingConfig(buy_amount_sol=0.05),
            risk=RiskConfig(daily_sol_limit=0.5)
        )
        
        assert settings.trading.buy_amount_sol == 0.05
        assert settings.risk.daily_sol_limit == 0.5