"""Main application entrypoint for the Solana meme coin sniping bot."""

import argparse
import asyncio
import json
import signal
import sys
import time
from typing import Optional

import websocket
from solders.pubkey import Pubkey

from .clients.solana import health_check, async_health_check, close_clients
from .config import settings
from .db import init_database, close_database
from .keys import validate_keypair
from .logging import get_logger, set_correlation_id
from .risk import get_risk_status
from .services.notifications import send_system_alert
from .services.trading import evaluate_token, get_active_trades

logger = get_logger(__name__)


class MemeSnipingBot:
    """Main bot orchestrator."""
    
    def __init__(self):
        self.running = False
        self.websocket: Optional[websocket.WebSocketApp] = None
        self.pump_fun_program_id = Pubkey.from_string(settings.pump_fun_program_id)
        
    async def startup(self) -> None:
        """Initialize bot systems."""
        logger.info("Bot startup initiated", extra={'event': 'bot_startup'})
        
        try:
            # Validate configuration
            logger.info("Validating configuration...")
            await self._validate_configuration()
            
            # Initialize database
            logger.info("Initializing database...")
            await init_database()
            
            # Validate systems
            logger.info("Validating systems...")
            await self._validate_systems()
            
            # Send startup notification
            await send_system_alert(
                f"Bot started successfully | "
                f"Dry run: {settings.dry_run} | "
                f"Buy amount: {settings.trading.buy_amount_sol} SOL"
            )
            
            logger.info(
                "Bot startup completed successfully",
                extra={
                    'dry_run': settings.dry_run,
                    'buy_amount_sol': settings.trading.buy_amount_sol,
                    'event': 'bot_startup_completed'
                }
            )
            
        except Exception as e:
            logger.error(
                "Bot startup failed",
                extra={'error': str(e), 'event': 'bot_startup_failed'}
            )
            await send_system_alert(f"Bot startup failed: {str(e)}")
            raise
    
    async def _validate_configuration(self) -> None:
        """Validate configuration and environment."""
        # Configuration is already validated by Pydantic in config.py
        logger.info(
            "Configuration validated",
            extra={
                'solana_rpc': settings.solana_rpc,
                'dry_run': settings.dry_run,
                'log_level': settings.log_level,
                'event': 'config_validated'
            }
        )
        
        # Validate keypair
        if not validate_keypair():
            raise ValueError("Keypair validation failed")
    
    async def _validate_systems(self) -> None:
        """Validate external system connections."""
        # Check Solana RPC
        if not health_check():
            raise ConnectionError("Solana RPC health check failed")
        
        if not await async_health_check():
            raise ConnectionError("Async Solana RPC health check failed")
        
        logger.info("System validation completed", extra={'event': 'system_validation_completed'})
    
    def start_websocket_monitoring(self) -> None:
        """Start WebSocket monitoring for new tokens."""
        ws_url = settings.solana_rpc.replace("https", "wss").replace("http", "ws")
        
        logger.info(
            "Starting WebSocket monitoring",
            extra={
                'ws_url': ws_url,
                'pump_fun_program_id': str(self.pump_fun_program_id),
                'event': 'websocket_monitoring_started'
            }
        )
        
        self.websocket = websocket.WebSocketApp(
            ws_url,
            on_open=self._on_websocket_open,
            on_message=self._on_websocket_message,
            on_error=self._on_websocket_error,
            on_close=self._on_websocket_close
        )
        
        # Run WebSocket in a separate thread
        import threading
        ws_thread = threading.Thread(target=self.websocket.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
    
    def _on_websocket_open(self, ws) -> None:
        """Handle WebSocket connection open."""
        logger.info("WebSocket connection opened", extra={'event': 'websocket_opened'})
        
        # Subscribe to logs mentioning pump.fun program
        subscription = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [str(self.pump_fun_program_id)]},
                {"commitment": "processed"}
            ]
        }
        
        ws.send(json.dumps(subscription))
        logger.info("Subscribed to pump.fun logs", extra={'event': 'logs_subscribed'})
    
    def _on_websocket_message(self, ws, message: str) -> None:
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            # Skip subscription confirmations
            if 'result' in data:
                return
            
            # Extract log data
            log_data = data.get('params', {}).get('result', {}).get('value', {})
            logs = log_data.get('logs', [])
            
            if not logs:
                return
            
            # Check if this looks like a new token initialization
            log_text = ' '.join(logs).lower()
            if str(self.pump_fun_program_id) in log_text and 'initialize' in log_text:
                # Extract token mint (this is a simplified extraction)
                token_mint = self._extract_token_mint(logs)
                if token_mint:
                    # Schedule token evaluation
                    asyncio.create_task(self._handle_new_token(token_mint))
                    
        except Exception as e:
            logger.error(
                "Error processing WebSocket message",
                extra={
                    'error': str(e),
                    'message_preview': message[:100],
                    'event': 'websocket_message_error'
                }
            )
    
    def _extract_token_mint(self, logs: list[str]) -> Optional[str]:
        """Extract token mint from log messages."""
        # This is a simplified implementation
        # In production, you'd use a proper log parser for Solana programs
        for log in logs:
            if 'Mint' in log:
                parts = log.split()
                for i, part in enumerate(parts):
                    if part == 'Mint:' and i + 1 < len(parts):
                        potential_mint = parts[i + 1]
                        try:
                            # Validate it's a valid Solana public key
                            Pubkey.from_string(potential_mint)
                            return potential_mint
                        except:
                            continue
        return None
    
    async def _handle_new_token(self, token_mint: str) -> None:
        """Handle discovery of a new token."""
        set_correlation_id()
        
        logger.info(
            "New token discovered",
            extra={
                'token_mint': token_mint,
                'event': 'new_token_discovered'
            }
        )
        
        try:
            # Evaluate token for trading
            trade_id = await evaluate_token(token_mint)
            
            if trade_id:
                logger.info(
                    "Trade initiated for new token",
                    extra={
                        'token_mint': token_mint,
                        'trade_id': trade_id,
                        'event': 'trade_initiated_new_token'
                    }
                )
            else:
                logger.info(
                    "Token evaluation did not result in trade",
                    extra={
                        'token_mint': token_mint,
                        'event': 'token_evaluation_no_trade'
                    }
                )
                
        except Exception as e:
            logger.error(
                "Error handling new token",
                extra={
                    'token_mint': token_mint,
                    'error': str(e),
                    'event': 'new_token_handling_error'
                }
            )
    
    def _on_websocket_error(self, ws, error) -> None:
        """Handle WebSocket errors."""
        logger.error(
            "WebSocket error",
            extra={
                'error': str(error),
                'event': 'websocket_error'
            }
        )
    
    def _on_websocket_close(self, ws, close_status_code, close_msg) -> None:
        """Handle WebSocket connection close."""
        logger.warning(
            "WebSocket connection closed",
            extra={
                'close_status_code': close_status_code,
                'close_msg': close_msg,
                'event': 'websocket_closed'
            }
        )
    
    async def run(self) -> None:
        """Main bot execution loop."""
        self.running = True
        
        logger.info("Bot main loop started", extra={'event': 'bot_main_loop_started'})
        
        # Start WebSocket monitoring
        self.start_websocket_monitoring()
        
        # Status reporting loop
        last_status_report = 0
        status_report_interval = 300  # 5 minutes
        
        try:
            while self.running:
                # Periodic status reporting
                current_time = time.time()
                if current_time - last_status_report > status_report_interval:
                    await self._report_status()
                    last_status_report = current_time
                
                # Sleep briefly to prevent busy loop
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal", extra={'event': 'interrupt_received'})
        except Exception as e:
            logger.error(
                "Error in main loop",
                extra={'error': str(e), 'event': 'main_loop_error'}
            )
        finally:
            await self.shutdown()
    
    async def _report_status(self) -> None:
        """Report bot status."""
        active_trades = get_active_trades()
        risk_status = get_risk_status()
        
        logger.info(
            "Bot status report",
            extra={
                'active_trades_count': len(active_trades),
                'risk_status': risk_status,
                'event': 'bot_status_report'
            }
        )
        
        # Send status to notifications if there are active trades
        if active_trades:
            trade_summaries = []
            for trade_id, trade in active_trades.items():
                pnl = trade.calculate_pnl() or 0
                trade_summaries.append(f"{trade.token_name}: {pnl:+.2f}%")
            
            status_msg = f"Active trades ({len(active_trades)}): {', '.join(trade_summaries)}"
            await send_system_alert(status_msg)
    
    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Bot shutdown initiated", extra={'event': 'bot_shutdown'})
        
        self.running = False
        
        # Close WebSocket connection
        if self.websocket:
            self.websocket.close()
        
        # Close database connections
        await close_database()
        
        # Close client connections
        await close_clients()
        
        # Send shutdown notification
        await send_system_alert("Bot shutdown completed")
        
        logger.info("Bot shutdown completed", extra={'event': 'bot_shutdown_completed'})


async def main() -> None:
    """Main entrypoint function."""
    parser = argparse.ArgumentParser(description="Advanced Meme Fun Snipper Bot")
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no actual trades)')
    parser.add_argument('--status', action='store_true', help='Show status and exit')
    
    args = parser.parse_args()
    
    # Override dry-run setting if specified
    if args.dry_run:
        settings.dry_run = True
    
    if args.status:
        # Show status and exit
        try:
            await init_database()
            risk_status = get_risk_status()
            active_trades = get_active_trades()
            
            print(f"Bot Status:")
            print(f"  Dry Run: {settings.dry_run}")
            print(f"  Active Trades: {len(active_trades)}")
            print(f"  Risk Status: {risk_status}")
            
            return
        except Exception as e:
            print(f"Error getting status: {e}")
            sys.exit(1)
    
    # Create and run bot
    bot = MemeSnipingBot()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}", extra={'event': 'signal_received'})
        asyncio.create_task(bot.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.startup()
        await bot.run()
    except Exception as e:
        logger.error(
            "Bot execution failed",
            extra={'error': str(e), 'event': 'bot_execution_failed'}
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())