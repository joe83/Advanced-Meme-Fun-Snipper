"""Test configuration for pytest."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

# Test configuration
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from snipper.config import Settings, TradingConfig, RiskConfig
    
    trading_config = TradingConfig(
        buy_amount_sol=0.01,
        min_liquidity_usd=1000,
        min_market_cap_usd=2000,
        take_profit_multiplier=2.0,
        stop_loss_multiplier=0.7,
        trailing_stop_percent=10.0,
        max_hold_time_min=30,
        price_check_interval_sec=1,
        slippage_bps=50,
        jito_base_tip=100_000
    )
    
    risk_config = RiskConfig(
        daily_sol_limit=1.0,
        max_consecutive_failures=3,
        circuit_breaker_cooldown_min=5,
        max_slippage_percent=5.0
    )
    
    settings = Settings(
        solana_rpc="https://api.mainnet-beta.solana.com",
        private_key="5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXp4c6afB5wuF"*2,  # Mock key
        xai_api_key="test_xai_key",
        birdeye_api_key="test_birdeye_key",
        mongo_uri="mongodb://localhost:27017/test",
        db_name="test_sniper_bot",
        collection_name="test_trades",
        telegram_token=None,
        telegram_channel=None,
        pump_fun_program_id="6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
        sol_mint="So11111111111111111111111111111111111111112",
        grok_model="grok-4",
        trading=trading_config,
        risk=risk_config,
        dry_run=True,
        log_level="DEBUG"
    )
    
    return settings


@pytest.fixture
def mock_mongo_client():
    """Mock MongoDB client."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    
    mock_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    
    return mock_client


@pytest.fixture
def mock_solana_client():
    """Mock Solana RPC client."""
    mock_client = MagicMock()
    mock_client.get_health.return_value.value = "ok"
    return mock_client


@pytest.fixture
def mock_async_solana_client():
    """Mock async Solana RPC client."""
    mock_client = AsyncMock()
    mock_client.get_health.return_value.value = "ok"
    return mock_client