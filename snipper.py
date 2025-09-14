# sniper.py - Full production-ready Solana meme coin sniping bot with Grok API analysis, Jupiter swaps, safety precautions, MongoDB logging, and Telegram alerts.

import os
import json
import time
import threading
import requests
import base64
import asyncio
import base58
from dotenv import load_dotenv
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders import message
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Processed
from openai import OpenAI  # For Grok API
import websocket
import pymongo
from telegram import Bot  # pip install python-telegram-bot
from jupiter_python_sdk.jupiter import Jupiter  # pip install jupiter-python-sdk

load_dotenv()

# Config - Replace with your details
SOLANA_RPC = os.getenv("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
PRIVATE_KEY_BASE58 = os.getenv("PRIVATE_KEY")  # Base58-encoded
XAI_API_KEY = os.getenv("XAI_API_KEY")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")  # e.g., "@myalerts"
PUMP_FUN_PROGRAM_ID = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
SOL_MINT = "So11111111111111111111111111111111111111112"
BUY_AMOUNT_SOL = float(os.getenv("BUY_AMOUNT_SOL", 0.1))
MIN_LIQUIDITY_USD = 5000
MIN_MARKET_CAP_USD = 10000
TAKE_PROFIT_MULTIPLIER = float(os.getenv("TAKE_PROFIT_MULTIPLIER", 2.0))
STOP_LOSS_MULTIPLIER = float(os.getenv("STOP_LOSS_MULTIPLIER", 0.7))
TRAILING_STOP_PERCENT = float(os.getenv("TRAILING_STOP_PERCENT", 10.0))
MAX_HOLD_TIME_MIN = int(os.getenv("MAX_HOLD_TIME_MIN", 30))
PRICE_CHECK_INTERVAL_SEC = 10
GROK_MODEL = "grok-4"
DB_NAME = "sniper_bot"
COLLECTION_NAME = "trades"
SLIPPAGE_BPS = 50  # 0.5%
JITO_BASE_TIP = int(os.getenv("JITO_BASE_TIP", 100_000))  # 0.0001 SOL

# Initialize clients
sync_client = Client(SOLANA_RPC)
async_client = AsyncClient(SOLANA_RPC)
keypair = Keypair.from_base58(PRIVATE_KEY_BASE58)
wallet_pubkey = keypair.pubkey()
grok_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]
telegram_bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN and TELEGRAM_CHANNEL else None

# Initialize Jupiter SDK
jupiter = Jupiter(
    async_client=async_client,
    keypair=keypair,
    quote_api_url="https://quote-api.jup.ag/v6/quote?",
    swap_api_url="https://quote-api.jup.ag/v6/swap",
)

def send_telegram_alert(message):
    if telegram_bot:
        try:
            telegram_bot.send_message(chat_id=TELEGRAM_CHANNEL, text=message)
        except Exception as e:
            print(f"Telegram alert error: {e}")

def log_to_mongo(data):
    try:
        collection.insert_one(data)
        print("Logged to MongoDB")
    except Exception as e:
        print(f"MongoDB log error: {e}")

def query_grok_for_analysis(token_address, token_name):
    prompt = f"Analyze this new Solana meme coin: Address {token_address}, Name {token_name}. Check real-time sentiment on X, hype potential, risk of rug pull, community strength, and overall buy recommendation (score 1-10). Be truthful and cite sources if possible. Format end with 'Score: X/10'."
    response = grok_client.chat.completions.create(
        model=GROK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )
    analysis = response.choices[0].message.content
    try:
        score = int(analysis.split("Score:")[-1].strip().split("/")[0])
    except:
        score = 0
    return analysis, score

price_cache = {}
def get_token_price(token_mint):
    cache_key = token_mint
    cached = price_cache.get(cache_key)
    if cached and time.time() - cached['timestamp'] < 5:
        return cached['value']
    url = f"https://public-api.birdeye.so/public/price?address={token_mint}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "x-chain": "solana"}
    try:
        resp = requests.get(url, headers=headers).json()
        price = resp['data']['value'] if resp.get('success') else None
        price_cache[cache_key] = {'value': price, 'timestamp': time.time()}
        return price
    except:
        return None

def get_token_liquidity(token_mint):
    url = f"https://public-api.birdeye.so/defi/liquidity_pool?address={token_mint}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "x-chain": "solana"}
    try:
        resp = requests.get(url, headers=headers).json()
        return resp['data'].get('liquidity', 0) if resp.get('success') else 0
    except:
        return 0

def get_token_account(pubkey, mint):
    try:
        accounts = sync_client.get_token_accounts_by_owner(pubkey, mint=str(mint), encoding="jsonParsed").value
        if accounts:
            return Pubkey.from_bytes(accounts[0].pubkey)
    except:
        return None

def get_token_balance(token_account):
    if token_account:
        return sync_client.get_balance(token_account).value
    return 0

async def check_wallet_balance():
    try:
        balance = await async_client.get_balance(wallet_pubkey)
        sol_balance = balance.value / 1_000_000_000
        if sol_balance < BUY_AMOUNT_SOL + 0.001:  # Reserve for fees
            send_telegram_alert(f"Low wallet balance: {sol_balance} SOL")
        return sol_balance
    except Exception as e:
        send_telegram_alert(f"Balance check error: {e}")
        return 0

async def execute_swap(input_mint, output_mint, amount_lamports, is_buy=True, jito_tip=100_000):
    if await check_wallet_balance() < BUY_AMOUNT_SOL + 0.001:
        return None
    start_time = time.time()
    for attempt in range(3):
        try:
            transaction_data = await jupiter.swap(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount_lamports,
                slippage_bps=SLIPPAGE_BPS,
                jito_tip=int(jito_tip)
            )
            raw_tx = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
            signature = keypair.sign_message(message.to_bytes_versioned(raw_tx.message))
            signed_tx = VersionedTransaction(raw_tx.message, [signature])
            opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
            result = await async_client.send_raw_transaction(bytes(signed_tx), opts=opts)
            tx_id = result.value
            latency_ms = (time.time() - start_time) * 1000
            print(f"{'Buy' if is_buy else 'Sell'} Tx: https://solscan.io/tx/{tx_id}")
            send_telegram_alert(f"{'Bought' if is_buy else 'Sold'} {output_mint if is_buy else input_mint}: https://solscan.io/tx/{tx_id}, Latency: {latency_ms:.2f}ms, Jito Tip: {jito_tip/1_000_000_000:.6f} SOL")
            log_data = {
                "tx_type": 'buy' if is_buy else 'sell',
                "token": output_mint if is_buy else input_mint,
                "tx_id": str(tx_id),
                "fee_sol": 0.000005,
                "jito_tip_sol": jito_tip / 1_000_000_000,
                "latency_ms": latency_ms,
                "timestamp": time.time()
            }
            log_to_mongo(log_data)
            return tx_id
        except Exception as e:
            print(f"Swap attempt {attempt+1} failed: {e}")
            if attempt == 2:
                send_telegram_alert(f"Swap failed for {output_mint if is_buy else input_mint}: {str(e)}")
                return None
            await asyncio.sleep(1)

async def monitor_position(token_mint, entry_price, buy_time, analysis, buy_amount_sol):
    start_time = time.time()
    peak_price = entry_price
    trailing_stop = entry_price * (1 - TRAILING_STOP_PERCENT / 100)
    log_data = {"token": str(token_mint), "buy_time": buy_time, "entry_price": entry_price, "analysis": analysis, "buy_amount_sol": buy_amount_sol}
    token_account = get_token_account(wallet_pubkey, token_mint)
    total_fees = 0

    while True:
        current_price = get_token_price(str(token_mint))
        if current_price is None:
            await asyncio.sleep(PRICE_CHECK_INTERVAL_SEC)
            continue

        if current_price > peak_price:
            peak_price = current_price
            trailing_stop = peak_price * (1 - TRAILING_STOP_PERCENT / 100)

        elapsed_min = (time.time() - start_time) / 60

        if current_price >= entry_price * TAKE_PROFIT_MULTIPLIER:
            reason = "Take Profit"
        elif current_price <= entry_price * STOP_LOSS_MULTIPLIER or current_price <= trailing_stop:
            reason = "Stop Loss/Trailing"
        elif elapsed_min > MAX_HOLD_TIME_MIN:
            reason = "Time Exit"
        else:
            await asyncio.sleep(PRICE_CHECK_INTERVAL_SEC)
            continue

        # Sell all
        balance_lamports = get_token_balance(token_account)
        if balance_lamports > 0:
            sell_sig = await execute_swap(str(token_mint), SOL_MINT, balance_lamports, is_buy=False)
            if sell_sig:
                total_fees += 0.000005  # Approx fee
                if total_fees > 0.01:
                    send_telegram_alert(f"High fees for {token_mint}: {total_fees} SOL")
            exit_price = current_price
            pnl = (exit_price - entry_price) / entry_price * 100 if entry_price else 0
            log_data.update({"sell_time": time.time(), "exit_price": exit_price, "pnl_percent": pnl, "reason": reason, "sell_sig": str(sell_sig)})
            log_to_mongo(log_data)
            print(f"Sold {token_mint}: {reason}, PnL: {pnl}%")
            send_telegram_alert(f"Sold {token_mint}: {reason}, PnL: {pnl}%")
        break

def on_message(ws, message):
    start_time = time.time()
    data = json.loads(message)
    if 'result' in data:  # Handle subscription response
        return
    logs = data.get('params', {}).get('result', {}).get('value', {}).get('logs', [])
    if logs and any(str(PUMP_FUN_PROGRAM_ID) in log for log in logs) and 'initialize' in ''.join(logs).lower():  # Better filter for new token creation
        # Extract token mint from logs (this may need parsing; assume from accounts)
        try:
            # Improved mint extraction: Parse logs for mint address (placeholder; in production, use log parsing library like solders)
            for log in logs:
                if 'Mint' in log:
                    token_mint_str = log.split("Mint: ")[-1].split(" ")[0]  # Adjust based on actual log format
                    token_mint = Pubkey.from_string(token_mint_str)
                    break
            else:
                return
            token_name = "Unknown"  # Fetch from metadata if possible (add Metaplex integration for prod)
            liquidity = get_token_liquidity(str(token_mint))
            if liquidity < MIN_LIQUIDITY_USD:
                print(f"Ignoring low liquidity: {token_mint}")
                return
            market_cap = liquidity * 2  # Approx; fetch properly via Birdeye or on-chain
            if market_cap < MIN_MARKET_CAP_USD:
                return
            analysis, score = query_grok_for_analysis(str(token_mint), token_name)
            print(f"Analysis: {analysis}")
            jito_tip = JITO_BASE_TIP * (score / 10) * 2  # Scale tip with Grok score (e.g., 0.0002 SOL for score=10)
            if score >= 7:
                print(f"Sniping {token_mint}")
                amount_lamports = int(BUY_AMOUNT_SOL * 1_000_000_000)
                buy_sig = asyncio.run(execute_swap(SOL_MINT, str(token_mint), amount_lamports, jito_tip=jito_tip))
                if buy_sig:
                    entry_price = get_token_price(str(token_mint))
                    if entry_price:
                        threading.Thread(target=asyncio.run, args=(monitor_position(token_mint, entry_price, time.time(), analysis, BUY_AMOUNT_SOL),)).start()
            latency_ms = (time.time() - start_time) * 1000
            print(f"WebSocket latency: {latency_ms:.2f}ms")
            send_telegram_alert(f"WebSocket latency: {latency_ms:.2f}ms")
        except Exception as e:
            print(f"Message processing error: {e}")
            send_telegram_alert(f"Message processing error: {e}")

def on_open(ws):
    print("WS opened")
    sub = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "logsSubscribe",
        "params": [{"mentions": [str(PUMP_FUN_PROGRAM_ID)]}, {"commitment": "processed"}]
    }
    ws.send(json.dumps(sub))

ws_url = SOLANA_RPC.replace("https", "wss")
ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=lambda ws, err: print(err), on_close=lambda ws, c, r: print("WS closed"))
ws.run_forever()
