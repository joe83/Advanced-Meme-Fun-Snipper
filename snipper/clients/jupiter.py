"""Jupiter DEX client for swap operations."""

import base64
import time
from typing import Optional

from jupiter_python_sdk.jupiter import Jupiter
from solders import message
from solders.transaction import VersionedTransaction
from solana.rpc.commitment import Processed
from solana.rpc.types import TxOpts
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..keys import get_keypair
from ..logging import get_logger
from .solana import get_async_client

logger = get_logger(__name__)


class JupiterClient:
    """Jupiter DEX client with retry logic and error handling."""
    
    def __init__(self):
        self._jupiter: Optional[Jupiter] = None
    
    def get_jupiter(self) -> Jupiter:
        """Get Jupiter SDK instance."""
        if self._jupiter is None:
            self._jupiter = Jupiter(
                async_client=get_async_client(),
                keypair=get_keypair(),
                quote_api_url="https://quote-api.jup.ag/v6/quote",
                swap_api_url="https://quote-api.jup.ag/v6/swap",
            )
            logger.info(
                "Jupiter client created",
                extra={'event': 'jupiter_client_created'}
            )
        return self._jupiter
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_quote(self, input_mint: str, output_mint: str, 
                       amount: int, slippage_bps: Optional[int] = None) -> dict:
        """Get quote for token swap."""
        slippage = slippage_bps or settings.trading.slippage_bps
        
        try:
            start_time = time.time()
            jupiter = self.get_jupiter()
            
            # TODO: Implement quote logic based on Jupiter SDK
            # For now, return a stub response
            quote = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippageBps': slippage,
                'estimatedOutput': amount * 0.99,  # Stub estimate
            }
            
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "Quote retrieved",
                extra={
                    'input_mint': input_mint,
                    'output_mint': output_mint,
                    'amount': amount,
                    'slippage_bps': slippage,
                    'latency_ms': latency_ms,
                    'event': 'quote_retrieved'
                }
            )
            
            return quote
            
        except Exception as e:
            logger.error(
                "Failed to get quote",
                extra={
                    'input_mint': input_mint,
                    'output_mint': output_mint,
                    'amount': amount,
                    'error': str(e),
                    'event': 'quote_failed'
                }
            )
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def execute_swap(self, input_mint: str, output_mint: str, 
                          amount: int, slippage_bps: Optional[int] = None,
                          jito_tip: Optional[int] = None) -> Optional[str]:
        """Execute token swap via Jupiter."""
        slippage = slippage_bps or settings.trading.slippage_bps
        tip = jito_tip or settings.trading.jito_base_tip
        
        if settings.dry_run:
            logger.info(
                "DRY RUN: Would execute swap",
                extra={
                    'input_mint': input_mint,
                    'output_mint': output_mint,
                    'amount': amount,
                    'slippage_bps': slippage,
                    'jito_tip': tip,
                    'event': 'dry_run_swap'
                }
            )
            return "dry_run_tx_signature"
        
        try:
            start_time = time.time()
            jupiter = self.get_jupiter()
            async_client = get_async_client()
            keypair = get_keypair()
            
            # TODO: Implement actual swap execution based on Jupiter SDK
            # This is a stub implementation for the refactoring
            transaction_data = await jupiter.swap(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=slippage,
                jito_tip=tip
            )
            
            # Sign and send transaction
            raw_tx = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
            signature = keypair.sign_message(message.to_bytes_versioned(raw_tx.message))
            signed_tx = VersionedTransaction(raw_tx.message, [signature])
            
            opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
            result = await async_client.send_raw_transaction(bytes(signed_tx), opts=opts)
            tx_id = str(result.value)
            
            latency_ms = (time.time() - start_time) * 1000
            
            logger.info(
                "Swap executed successfully",
                extra={
                    'input_mint': input_mint,
                    'output_mint': output_mint,
                    'amount': amount,
                    'tx_id': tx_id,
                    'latency_ms': latency_ms,
                    'jito_tip': tip,
                    'event': 'swap_executed'
                }
            )
            
            return tx_id
            
        except Exception as e:
            logger.error(
                "Swap execution failed",
                extra={
                    'input_mint': input_mint,
                    'output_mint': output_mint,
                    'amount': amount,
                    'error': str(e),
                    'event': 'swap_failed'
                }
            )
            raise


# Global Jupiter client instance
jupiter_client = JupiterClient()


async def get_quote(input_mint: str, output_mint: str, amount: int,
                   slippage_bps: Optional[int] = None) -> dict:
    """Get quote for token swap."""
    return await jupiter_client.get_quote(input_mint, output_mint, amount, slippage_bps)


async def execute_swap(input_mint: str, output_mint: str, amount: int,
                      slippage_bps: Optional[int] = None,
                      jito_tip: Optional[int] = None) -> Optional[str]:
    """Execute token swap."""
    return await jupiter_client.execute_swap(input_mint, output_mint, amount, slippage_bps, jito_tip)