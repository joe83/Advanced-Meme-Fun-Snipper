"""Solana RPC client factory and health check utilities."""

from typing import Optional

from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)


class SolanaClientManager:
    """Manages Solana RPC client connections with health checks."""
    
    def __init__(self):
        self._sync_client: Optional[Client] = None
        self._async_client: Optional[AsyncClient] = None
    
    def get_sync_client(self) -> Client:
        """Get synchronous Solana RPC client."""
        if self._sync_client is None:
            self._sync_client = Client(settings.solana_rpc)
            logger.info(
                "Synchronous Solana client created",
                extra={
                    'rpc_url': settings.solana_rpc,
                    'event': 'sync_client_created'
                }
            )
        return self._sync_client
    
    def get_async_client(self) -> AsyncClient:
        """Get asynchronous Solana RPC client."""
        if self._async_client is None:
            self._async_client = AsyncClient(settings.solana_rpc)
            logger.info(
                "Asynchronous Solana client created",
                extra={
                    'rpc_url': settings.solana_rpc,
                    'event': 'async_client_created'
                }
            )
        return self._async_client
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def health_check(self) -> bool:
        """Perform health check on Solana RPC connection."""
        try:
            client = self.get_sync_client()
            result = client.get_health()
            
            if result.value == "ok":
                logger.info(
                    "Solana RPC health check passed",
                    extra={
                        'rpc_url': settings.solana_rpc,
                        'event': 'health_check_passed'
                    }
                )
                return True
            else:
                logger.warning(
                    "Solana RPC health check failed",
                    extra={
                        'rpc_url': settings.solana_rpc,
                        'health_status': result.value,
                        'event': 'health_check_failed'
                    }
                )
                return False
                
        except Exception as e:
            logger.error(
                "Solana RPC health check error",
                extra={
                    'rpc_url': settings.solana_rpc,
                    'error': str(e),
                    'event': 'health_check_error'
                }
            )
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def async_health_check(self) -> bool:
        """Perform asynchronous health check on Solana RPC connection."""
        try:
            client = self.get_async_client()
            result = await client.get_health()
            
            if result.value == "ok":
                logger.info(
                    "Solana RPC async health check passed",
                    extra={
                        'rpc_url': settings.solana_rpc,
                        'event': 'async_health_check_passed'
                    }
                )
                return True
            else:
                logger.warning(
                    "Solana RPC async health check failed",
                    extra={
                        'rpc_url': settings.solana_rpc,
                        'health_status': result.value,
                        'event': 'async_health_check_failed'
                    }
                )
                return False
                
        except Exception as e:
            logger.error(
                "Solana RPC async health check error",
                extra={
                    'rpc_url': settings.solana_rpc,
                    'error': str(e),
                    'event': 'async_health_check_error'
                }
            )
            raise
    
    async def close(self):
        """Close async client connections."""
        if self._async_client:
            await self._async_client.close()
            logger.info(
                "Async Solana client closed",
                extra={'event': 'async_client_closed'}
            )


# Global client manager instance
client_manager = SolanaClientManager()


def get_sync_client() -> Client:
    """Get synchronous Solana RPC client."""
    return client_manager.get_sync_client()


def get_async_client() -> AsyncClient:
    """Get asynchronous Solana RPC client."""
    return client_manager.get_async_client()


def health_check() -> bool:
    """Perform Solana RPC health check."""
    return client_manager.health_check()


async def async_health_check() -> bool:
    """Perform asynchronous Solana RPC health check."""
    return await client_manager.async_health_check()


async def close_clients():
    """Close all client connections."""
    await client_manager.close()