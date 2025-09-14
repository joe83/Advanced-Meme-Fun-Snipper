"""Trading orchestration service."""

import asyncio
import time
import uuid
from typing import Optional

from ..clients.jupiter import execute_swap
from ..config import settings
from ..db import get_trade_repository
from ..logging import get_logger, set_correlation_id, TradeLogger
from ..models.trade import Trade, TradeStatus, TradeSide, CloseReason, SwapEvent
from ..risk import can_trade, record_trade_success, record_trade_failure
from ..services.analysis import analyze_token
from ..services.notifications import send_trade_alert, send_error_alert
from ..services.pricing import get_token_price, get_token_liquidity, get_market_cap, create_trailing_stop

logger = get_logger(__name__)
trade_logger = TradeLogger()


class TradingService:
    """Orchestrates the complete trading lifecycle."""
    
    def __init__(self):
        self.active_trades = {}  # trade_id -> Trade
        self.trade_repository = get_trade_repository()
    
    async def evaluate_token(self, token_mint: str, token_name: Optional[str] = None) -> Optional[str]:
        """
        Evaluate a token for potential trading.
        
        Returns:
            Trade ID if trade was initiated, None otherwise
        """
        correlation_id = set_correlation_id()
        
        try:
            # Get basic token data
            liquidity = await get_token_liquidity(token_mint)
            market_cap = await get_market_cap(token_mint)
            
            logger.info(
                "Token evaluation started",
                extra={
                    'token_mint': token_mint,
                    'token_name': token_name,
                    'liquidity': liquidity,
                    'market_cap': market_cap,
                    'event': 'token_evaluation_started'
                }
            )
            
            # Apply filters
            if liquidity < settings.trading.min_liquidity_usd:
                logger.info(
                    "Token filtered out - low liquidity",
                    extra={
                        'token_mint': token_mint,
                        'liquidity': liquidity,
                        'min_required': settings.trading.min_liquidity_usd,
                        'event': 'token_filtered_liquidity'
                    }
                )
                return None
            
            if market_cap < settings.trading.min_market_cap_usd:
                logger.info(
                    "Token filtered out - low market cap",
                    extra={
                        'token_mint': token_mint,
                        'market_cap': market_cap,
                        'min_required': settings.trading.min_market_cap_usd,
                        'event': 'token_filtered_market_cap'
                    }
                )
                return None
            
            # Get AI analysis
            analysis_text, analysis_score = await analyze_token(token_mint, token_name)
            
            logger.info(
                "AI analysis completed",
                extra={
                    'token_mint': token_mint,
                    'analysis_score': analysis_score,
                    'event': 'ai_analysis_completed'
                }
            )
            
            # Check if score meets threshold
            if analysis_score < 7.0:  # Minimum score threshold
                logger.info(
                    "Token filtered out - low AI score",
                    extra={
                        'token_mint': token_mint,
                        'analysis_score': analysis_score,
                        'min_required': 7.0,
                        'event': 'token_filtered_ai_score'
                    }
                )
                return None
            
            # Check risk management
            can_trade_result, risk_reason = can_trade(settings.trading.buy_amount_sol)
            if not can_trade_result:
                logger.warning(
                    "Trade blocked by risk management",
                    extra={
                        'token_mint': token_mint,
                        'reason': risk_reason,
                        'event': 'trade_blocked_risk'
                    }
                )
                await send_error_alert("Risk Management", f"Trade blocked: {risk_reason}")
                return None
            
            # Initiate trade
            trade_id = await self._initiate_trade(
                token_mint=token_mint,
                token_name=token_name,
                analysis_text=analysis_text,
                analysis_score=analysis_score,
                liquidity=liquidity,
                market_cap=market_cap,
                correlation_id=correlation_id
            )
            
            return trade_id
            
        except Exception as e:
            logger.error(
                "Token evaluation failed",
                extra={
                    'token_mint': token_mint,
                    'error': str(e),
                    'event': 'token_evaluation_failed'
                }
            )
            await send_error_alert("Token Evaluation", f"Failed to evaluate {token_mint}: {str(e)}")
            return None
    
    async def _initiate_trade(self, token_mint: str, token_name: Optional[str],
                             analysis_text: str, analysis_score: float,
                             liquidity: float, market_cap: float,
                             correlation_id: str) -> str:
        """Initiate a new trade."""
        trade_id = str(uuid.uuid4())
        
        # Create trade record
        trade = Trade(
            trade_id=trade_id,
            token_mint=token_mint,
            token_name=token_name or "Unknown",
            analysis_text=analysis_text,
            analysis_score=analysis_score,
            buy_amount_sol=settings.trading.buy_amount_sol,
            liquidity_usd=liquidity,
            market_cap_usd=market_cap,
            correlation_id=correlation_id,
            status=TradeStatus.PENDING
        )
        
        # Save initial trade record
        await self.trade_repository.save_trade(trade)
        
        trade_logger.trade_started(trade_id, token_mint, analysis_score)
        
        try:
            # Execute buy order
            entry_price = await get_token_price(token_mint)
            if not entry_price:
                raise ValueError("Could not get token price")
            
            # Calculate Jito tip based on analysis score
            base_tip = settings.trading.jito_base_tip
            tip_multiplier = analysis_score / 10.0 * 2  # Scale by score
            jito_tip = int(base_tip * tip_multiplier)
            
            # Execute swap
            amount_lamports = int(settings.trading.buy_amount_sol * 1_000_000_000)
            tx_signature = await execute_swap(
                input_mint=settings.sol_mint,
                output_mint=token_mint,
                amount=amount_lamports,
                jito_tip=jito_tip
            )
            
            if not tx_signature:
                raise ValueError("Swap execution failed")
            
            # Update trade with entry details
            trade.entry_price = entry_price
            trade.entry_timestamp = time.time()
            trade.status = TradeStatus.ACTIVE
            trade.current_price = entry_price
            trade.peak_price = entry_price
            
            # Record swap event
            swap_event = SwapEvent(
                side=TradeSide.BUY,
                token_mint=token_mint,
                amount=amount_lamports,
                tx_signature=tx_signature,
                fee_sol=0.000005,  # Estimate
                jito_tip_sol=jito_tip / 1_000_000_000
            )
            trade.add_swap_event(swap_event)
            
            # Save updated trade
            await self.trade_repository.save_trade(trade)
            
            # Record success with risk manager
            record_trade_success(settings.trading.buy_amount_sol)
            
            # Add to active trades
            self.active_trades[trade_id] = trade
            
            # Send notification
            await send_trade_alert(
                trade_id,
                f"Bought {token_name} at ${entry_price:.6f} | Score: {analysis_score}/10 | "
                f"TX: https://solscan.io/tx/{tx_signature}"
            )
            
            trade_logger.swap_executed(trade_id, tx_signature, "buy", amount_lamports, 0)
            
            # Start position monitoring
            asyncio.create_task(self._monitor_position(trade))
            
            logger.info(
                "Trade initiated successfully",
                extra={
                    'trade_id': trade_id,
                    'token_mint': token_mint,
                    'entry_price': entry_price,
                    'tx_signature': tx_signature,
                    'event': 'trade_initiated'
                }
            )
            
            return trade_id
            
        except Exception as e:
            # Record failure
            record_trade_failure("swap_execution")
            trade.status = TradeStatus.FAILED
            await self.trade_repository.save_trade(trade)
            
            trade_logger.trade_error(trade_id, "execution_failed", str(e))
            await send_error_alert("Trade Execution", f"Failed to execute trade {trade_id}: {str(e)}")
            
            raise
    
    async def _monitor_position(self, trade: Trade) -> None:
        """Monitor an active position for exit conditions."""
        trade_id = trade.trade_id
        set_correlation_id(trade.correlation_id)
        
        logger.info(
            "Position monitoring started",
            extra={
                'trade_id': trade_id,
                'token_mint': trade.token_mint,
                'event': 'position_monitoring_started'
            }
        )
        
        # Initialize trailing stop
        trailing_stop = create_trailing_stop(
            entry_price=trade.entry_price,
            trailing_percent=settings.trading.trailing_stop_percent
        )
        
        start_time = time.time()
        
        try:
            while trade.status == TradeStatus.ACTIVE:
                # Get current price
                current_price = await get_token_price(trade.token_mint)
                if not current_price:
                    await asyncio.sleep(settings.trading.price_check_interval_sec)
                    continue
                
                trade.current_price = current_price
                trade.update_peak_price(current_price)
                
                # Check exit conditions
                exit_reason = None
                
                # Take profit
                if current_price >= trade.entry_price * settings.trading.take_profit_multiplier:
                    exit_reason = CloseReason.TAKE_PROFIT
                
                # Stop loss
                elif current_price <= trade.entry_price * settings.trading.stop_loss_multiplier:
                    exit_reason = CloseReason.STOP_LOSS
                
                # Trailing stop
                elif trailing_stop.update(current_price):
                    exit_reason = CloseReason.TRAILING_STOP
                
                # Time exit
                elif (time.time() - start_time) / 60 > settings.trading.max_hold_time_min:
                    exit_reason = CloseReason.TIME_EXIT
                
                if exit_reason:
                    await self._close_position(trade, exit_reason)
                    break
                
                # Update trade in database periodically
                await self.trade_repository.save_trade(trade)
                
                # Wait for next check
                await asyncio.sleep(settings.trading.price_check_interval_sec)
                
        except Exception as e:
            logger.error(
                "Position monitoring error",
                extra={
                    'trade_id': trade_id,
                    'error': str(e),
                    'event': 'position_monitoring_error'
                }
            )
            await self._close_position(trade, CloseReason.ERROR)
    
    async def _close_position(self, trade: Trade, reason: CloseReason) -> None:
        """Close an active position."""
        trade_id = trade.trade_id
        
        try:
            # TODO: Get actual token balance from wallet
            # For now, assume we hold the full amount
            token_balance = int(trade.buy_amount_sol * 1_000_000_000)  # Stub
            
            # Execute sell
            tx_signature = await execute_swap(
                input_mint=trade.token_mint,
                output_mint=settings.sol_mint,
                amount=token_balance,
                is_buy=False
            )
            
            if tx_signature:
                # Record sell swap
                swap_event = SwapEvent(
                    side=TradeSide.SELL,
                    token_mint=trade.token_mint,
                    amount=token_balance,
                    tx_signature=tx_signature,
                    fee_sol=0.000005  # Estimate
                )
                trade.add_swap_event(swap_event)
                
                trade_logger.swap_executed(trade_id, tx_signature, "sell", token_balance, 0)
            
            # Close trade
            trade.close_trade(trade.current_price or trade.entry_price, reason)
            
            # Remove from active trades
            self.active_trades.pop(trade_id, None)
            
            # Save final trade state
            await self.trade_repository.save_trade(trade)
            
            # Send notification
            pnl_str = f"{trade.pnl_percent:+.2f}%" if trade.pnl_percent else "Unknown"
            await send_trade_alert(
                trade_id,
                f"Sold {trade.token_name} | Reason: {reason.value} | "
                f"PnL: {pnl_str} | Hold: {trade.hold_time_minutes:.1f}m"
            )
            
            trade_logger.trade_closed(
                trade_id, reason.value, trade.pnl_percent or 0, trade.hold_time_minutes or 0
            )
            
            logger.info(
                "Position closed successfully",
                extra={
                    'trade_id': trade_id,
                    'reason': reason.value,
                    'pnl_percent': trade.pnl_percent,
                    'hold_time_minutes': trade.hold_time_minutes,
                    'event': 'position_closed'
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to close position",
                extra={
                    'trade_id': trade_id,
                    'reason': reason.value,
                    'error': str(e),
                    'event': 'position_close_failed'
                }
            )
            
            trade.status = TradeStatus.FAILED
            await self.trade_repository.save_trade(trade)
            
            await send_error_alert("Position Close", f"Failed to close {trade_id}: {str(e)}")


# Global trading service instance
trading_service = TradingService()


async def evaluate_token(token_mint: str, token_name: Optional[str] = None) -> Optional[str]:
    """Evaluate a token for potential trading."""
    return await trading_service.evaluate_token(token_mint, token_name)


def get_active_trades() -> dict:
    """Get currently active trades."""
    return trading_service.active_trades.copy()