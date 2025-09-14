"""Configuration management with Pydantic validation."""

import os
from typing import Optional

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from solders.pubkey import Pubkey


class TradingConfig(BaseModel):
    """Trading parameters configuration."""
    
    buy_amount_sol: float = Field(default=0.1, gt=0, le=10.0)
    min_liquidity_usd: float = Field(default=5000, ge=0)
    min_market_cap_usd: float = Field(default=10000, ge=0)
    take_profit_multiplier: float = Field(default=2.0, gt=1.0, le=10.0)
    stop_loss_multiplier: float = Field(default=0.7, gt=0.0, lt=1.0)
    trailing_stop_percent: float = Field(default=10.0, gt=0, le=50.0)
    max_hold_time_min: int = Field(default=30, ge=1, le=1440)  # Max 24 hours
    price_check_interval_sec: int = Field(default=10, ge=1, le=300)
    slippage_bps: int = Field(default=50, ge=1, le=1000)  # 0.01% to 10%
    jito_base_tip: int = Field(default=100_000, ge=0, le=10_000_000)  # Max 0.01 SOL


class RiskConfig(BaseModel):
    """Risk management configuration."""
    
    daily_sol_limit: float = Field(default=1.0, gt=0, le=100.0)
    max_consecutive_failures: int = Field(default=5, ge=1, le=20)
    circuit_breaker_cooldown_min: int = Field(default=60, ge=1, le=1440)
    max_slippage_percent: float = Field(default=5.0, gt=0, le=20.0)


class Settings(BaseSettings):
    """Main application settings with validation."""
    
    # Solana Configuration
    solana_rpc: str = Field(default="https://api.mainnet-beta.solana.com")
    private_key: str = Field(..., min_length=32, description="Base58-encoded private key")
    
    # External API Keys
    xai_api_key: str = Field(..., min_length=10, description="xAI API key for Grok analysis")
    birdeye_api_key: str = Field(..., min_length=10, description="BirdEye API key")
    
    # Database
    mongo_uri: str = Field(default="mongodb://localhost:27017/")
    db_name: str = Field(default="sniper_bot")
    collection_name: str = Field(default="trades")
    
    # Notifications
    telegram_token: Optional[str] = Field(default=None, min_length=10)
    telegram_channel: Optional[str] = Field(default=None)
    
    # Constants
    pump_fun_program_id: str = Field(default="6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
    sol_mint: str = Field(default="So11111111111111111111111111111111111111112")
    grok_model: str = Field(default="grok-4")
    
    # Nested configs
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    
    # Runtime
    dry_run: bool = Field(default=False, description="Enable dry-run mode (no actual trades)")
    log_level: str = Field(default="INFO")
    
    @validator('solana_rpc')
    def validate_solana_rpc(cls, v: str) -> str:
        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('ws://') or v.startswith('wss://')):
            raise ValueError('SOLANA_RPC must be a valid HTTP/WS URL')
        return v
    
    @validator('private_key')
    def validate_private_key(cls, v: str) -> str:
        try:
            # Basic validation that it's a valid base58 string that could be a keypair
            import base58
            decoded = base58.b58decode(v)
            if len(decoded) != 64:  # Solana private keys are 64 bytes
                raise ValueError('Private key must be 64 bytes when decoded')
        except Exception as e:
            raise ValueError(f'Invalid private key format: {e}')
        return v
    
    @validator('pump_fun_program_id', 'sol_mint')
    def validate_pubkey(cls, v: str) -> str:
        try:
            Pubkey.from_string(v)
        except Exception as e:
            raise ValueError(f'Invalid Solana public key: {e}')
        return v
    
    class Config:
        env_file = '.env'
        env_nested_delimiter = '__'
        case_sensitive = False

    @classmethod
    def from_env(cls) -> 'Settings':
        """Load settings from environment with better error handling."""
        try:
            # Override defaults with environment variables
            env_overrides = {}
            
            # Trading config from env
            if os.getenv('BUY_AMOUNT_SOL'):
                env_overrides.setdefault('trading', {})['buy_amount_sol'] = float(os.getenv('BUY_AMOUNT_SOL'))
            if os.getenv('MIN_LIQUIDITY_USD'):
                env_overrides.setdefault('trading', {})['min_liquidity_usd'] = float(os.getenv('MIN_LIQUIDITY_USD'))
            if os.getenv('MIN_MARKET_CAP_USD'):
                env_overrides.setdefault('trading', {})['min_market_cap_usd'] = float(os.getenv('MIN_MARKET_CAP_USD'))
            if os.getenv('TAKE_PROFIT_MULTIPLIER'):
                env_overrides.setdefault('trading', {})['take_profit_multiplier'] = float(os.getenv('TAKE_PROFIT_MULTIPLIER'))
            if os.getenv('STOP_LOSS_MULTIPLIER'):
                env_overrides.setdefault('trading', {})['stop_loss_multiplier'] = float(os.getenv('STOP_LOSS_MULTIPLIER'))
            if os.getenv('TRAILING_STOP_PERCENT'):
                env_overrides.setdefault('trading', {})['trailing_stop_percent'] = float(os.getenv('TRAILING_STOP_PERCENT'))
            if os.getenv('MAX_HOLD_TIME_MIN'):
                env_overrides.setdefault('trading', {})['max_hold_time_min'] = int(os.getenv('MAX_HOLD_TIME_MIN'))
            if os.getenv('JITO_BASE_TIP'):
                env_overrides.setdefault('trading', {})['jito_base_tip'] = int(os.getenv('JITO_BASE_TIP'))
            
            # Apply overrides to model defaults
            if env_overrides.get('trading'):
                trading_config = TradingConfig(**env_overrides['trading'])
                env_overrides['trading'] = trading_config
            
            return cls(**env_overrides)
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")


def get_settings() -> Settings:
    """Get validated settings instance."""
    return Settings.from_env()


# Global settings instance (created on first import)
settings = get_settings()