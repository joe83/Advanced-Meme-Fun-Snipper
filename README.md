# Advanced Meme Fun Snipper

A production-ready, modular Solana meme coin sniping bot with AI analysis, risk management, and comprehensive monitoring.

## 🚀 Features

- **AI-Powered Analysis**: Grok API integration for token sentiment and hype analysis
- **Real-time Monitoring**: WebSocket monitoring of pump.fun for new token launches
- **Risk Management**: Circuit breakers, daily spending limits, slippage protection
- **Trading Automation**: Jupiter DEX integration with MEV protection via Jito tips
- **Structured Logging**: JSON logging with correlation IDs and sensitive data redaction
- **Database Persistence**: MongoDB storage with trade lifecycle tracking
- **Multi-channel Notifications**: Telegram alerts with extensible notification system
- **Dry Run Mode**: Strategy simulation without actual trades
- **Modular Architecture**: Clean separation of concerns for easy extension

## 📋 Requirements

- Python 3.10+
- MongoDB instance
- Solana RPC node (self-hosted recommended for low latency)
- API Keys: xAI (Grok), BirdEye, Telegram Bot (optional)
- Wallet with SOL for trades and fees

## 🔧 Installation

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd Advanced-Meme-Fun-Snipper
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Set Up Solana Node (Recommended)

For optimal performance, run a local Solana RPC node:

```bash
# Install Solana CLI
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"

# Run non-voting RPC node
solana-validator \
  --ledger /ledger \
  --rpc-port 8899 \
  --no-voting \
  --private-rpc \
  --dynamic-port-range 8000-8020 \
  --rpc-bind-address 127.0.0.1 \
  --enable-rpc-transaction-history \
  --enable-cpi-and-log-storage \
  --rpc-max-multiple-accounts 1000 \
  --rpc-pubsub-max-connections 1000
```

## 🚀 Usage

### Running the Bot

```bash
# Production mode
python -m snipper.main

# Dry run mode (no actual trades)
python -m snipper.main --dry-run

# Check status
python -m snipper.main --status
```

### Configuration Options

Key environment variables in `.env`:

```bash
# Solana Configuration
SOLANA_RPC=http://127.0.0.1:8899
PRIVATE_KEY=your_base58_private_key

# API Keys
XAI_API_KEY=your_xai_api_key
BIRDEYE_API_KEY=your_birdeye_api_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL=@your_channel

# Trading Parameters
BUY_AMOUNT_SOL=0.1
TAKE_PROFIT_MULTIPLIER=2.0
STOP_LOSS_MULTIPLIER=0.7
TRAILING_STOP_PERCENT=10.0
MAX_HOLD_TIME_MIN=30

# Risk Management
RISK_DAILY_SOL_LIMIT=1.0
RISK_MAX_CONSECUTIVE_FAILURES=5
RISK_MAX_SLIPPAGE_PERCENT=5.0

# Database
MONGO_URI=mongodb://localhost:27017/
```

## 🏗️ Architecture

### Project Structure

```
snipper/
├── __init__.py           # Package initialization
├── config.py             # Pydantic-based configuration
├── logging.py            # Structured logging setup
├── keys.py               # Secure keypair management
├── main.py               # Application entrypoint
├── clients/              # External service clients
│   ├── solana.py         # Solana RPC client factory
│   └── jupiter.py        # Jupiter DEX client
├── services/             # Core business logic
│   ├── trading.py        # Trade orchestration
│   ├── pricing.py        # Price monitoring & trailing stops
│   ├── analysis.py       # Grok AI integration
│   └── notifications.py  # Multi-channel alerts
├── models/               # Data models
│   └── trade.py          # Trade lifecycle models
├── db/                   # Database layer
│   └── mongo.py          # MongoDB repository
└── risk/                 # Risk management
    └── guards.py         # Circuit breakers & limits
```

### Key Components

- **Configuration**: Pydantic-based validation with environment variable mapping
- **Logging**: Structured JSON logging with correlation IDs and sensitive data redaction
- **Clients**: Solana RPC and Jupiter DEX clients with health checks and retry logic
- **Services**: Modular business logic for trading, pricing, analysis, and notifications
- **Risk Management**: Circuit breakers, spending limits, and slippage protection
- **Database**: Repository pattern for MongoDB with proper indexing

## 🧪 Testing

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=snipper

# Run specific test file
pytest tests/test_config.py -v
```

## 🛡️ Security Considerations

- **Private Key Protection**: Keys are validated but never logged
- **Environment Variables**: All sensitive config via environment variables
- **Dry Run Mode**: Test strategies without financial risk
- **Rate Limiting**: Built-in retry logic with exponential backoff
- **Spending Limits**: Daily SOL limits and circuit breakers

See [SECURITY.md](SECURITY.md) for detailed security guidelines.

## 📊 Monitoring & Observability

### Structured Logging

All logs include:
- Correlation IDs for request tracing
- Event types for filtering
- Performance metrics (latency, success rates)
- Sensitive data redaction

### Trade Tracking

Complete trade lifecycle stored in MongoDB:
- Entry/exit prices and timestamps
- PnL calculations and hold times
- Swap transaction signatures
- AI analysis scores and reasoning

### Risk Metrics

Real-time monitoring of:
- Daily spending vs. limits
- Circuit breaker status
- Consecutive failure counts
- Active trade performance

## 🔮 Future Enhancements

### Planned Features

- **Multi-chain Support**: Extend to other blockchain networks
- **Strategy Plugins**: Pluggable trading strategies
- **Advanced AI**: Enhanced token analysis with multiple models
- **Metrics Backend**: Prometheus/OpenTelemetry integration
- **Web Dashboard**: Real-time monitoring interface
- **Backtesting**: Historical strategy validation

### Plugin Architecture

The modular design supports easy extension:

1. **New Notification Channels**: Implement `NotificationChannel` interface
2. **Trading Strategies**: Extend `TradingService` with new evaluation logic
3. **Risk Guards**: Add custom risk management rules
4. **Data Sources**: Integrate additional price/analysis providers

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## ⚠️ Disclaimer

- Cryptocurrency trading involves significant financial risk
- This software is provided "as-is" without warranty
- Always test thoroughly with small amounts
- Use dry-run mode for strategy validation
- Ensure secure private key storage

## 🆘 Support

- Check logs for detailed error information
- Use `--status` flag for system health
- Monitor database for trade history
- Review risk management alerts

For issues and feature requests, please use the GitHub issue tracker.