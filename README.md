# README.md - Project documentation and setup guide

# Solana Meme Coin Sniping Bot

A production-ready bot for sniping new meme coins on Solana (e.g., pump.fun launches), with Grok API analysis, Jupiter swaps, safety precautions (stop-loss, trailing stops, time exits), MongoDB logging, and Telegram alerts.

## Features
- Monitors pump.fun for new token launches via WebSocket `logsSubscribe`.
- Analyzes tokens with Grok API for hype/sentiment/risk (score 1-10).
- Executes fast buys/sells via Jupiter Aggregator with dynamic Jito tips for MEV protection.
- Safety: Stop-loss, trailing stops, time-based exits, position monitoring.
- Logging: Trades/PnL to MongoDB.
- Alerts: Telegram notifications for trades, errors, latencies, low balance.
- Optimized for low-latency colocated Solana RPC node (e.g., Hetzner server).

## Requirements
- Python 3.10+
- Solana CLI and RPC node (non-voting) for colocation.
- Accounts: xAI API, Birdeye API, Telegram Bot, MongoDB.
- Wallet with SOL for trades/fees.

## Setup
1. **Install Dependencies**:
pip install -r requirements.txt

2. **Configure .env**:
Copy `.env.example` to `.env` and fill in values.

3. **Set Up Solana Node** (for colocation):
- Install Solana CLI: `sh -c "$(curl -sSfL https://release.solana.com/stable/install)"`
- Run non-voting RPC:
  ```
  solana-validator --ledger /ledger --rpc-port 8899 --no-voting --private-rpc --dynamic-port-range 8000-8020 --rpc-bind-address 127.0.0.1 --enable-rpc-transaction-history --enable-cpi-and-log-storage --rpc-max-multiple-accounts 1000 --rpc-pubsub-max-connections 1000
  ```
- Sync ledger (~2TB, 1-2 days).

4. **Optional: Jito Relayer** (for MEV bundles):
wget https://github.com/jito-labs/jito-relayer/releases/latest/download/jito-relayer chmod +x jito-relayer ./jito-relayer --rpc http://127.0.0.1:8899


5. **Run the Bot**:
python sniper.py

- For 24/7: Use PM2 (`pm2 start sniper.py --interpreter python3`).

## Testing
- Use devnet: `solana config set --url https://api.devnet.solana.com` and adjust node command with `--devnet`.
- Test with small BUY_AMOUNT_SOL=0.01.

## Customization
- Adjust thresholds in .env (e.g., TAKE_PROFIT_MULTIPLIER=3.0).
- Enhance mint extraction in `on_message` with better log parsing.
- Add metadata fetching (e.g., Metaplex for token names).

## Risks
- Crypto trading is high-risk; use small amounts.
- Test thoroughly; no guarantees on profits.
- Ensure secure PRIVATE_KEY storage.

## License
MIT License - Free to use and modify.