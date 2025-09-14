"""Token pricing service with BirdEye integration and caching."""

import time
from typing import Dict, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)


class PricingService:
    """Service for fetching token prices and liquidity data."""
    
    def __init__(self):
        self._price_cache: Dict[str, Dict[str, float]] = {}
        self._cache_ttl = 5.0  # Cache for 5 seconds
        self._birdeye_headers = {
            "X-API-KEY": settings.birdeye_api_key,
            "x-chain": "solana"
        }
    
    def is_available(self) -> bool:
        """Check if BirdEye API is configured."""
        return bool(settings.birdeye_api_key)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_token_price(self, token_mint: str) -> Optional[float]:
        """Get current token price in USD."""
        # Check cache first
        cached = self._get_cached_price(token_mint)
        if cached is not None:
            return cached
        
        if not self.is_available():
            logger.warning(
                "BirdEye API not configured",
                extra={'token_mint': token_mint, 'event': 'birdeye_not_configured'}
            )
            return None
        
        if settings.dry_run:
            # Return mock price that varies slightly for testing
            mock_price = 0.001 * (1 + (hash(token_mint) % 100) / 1000)
            logger.info(
                "DRY RUN: Mock token price",
                extra={
                    'token_mint': token_mint,
                    'price': mock_price,
                    'event': 'dry_run_price'
                }
            )
            self._cache_price(token_mint, mock_price)
            return mock_price
        
        try:
            url = f"https://public-api.birdeye.so/defi/price"
            params = {"address": token_mint}
            
            response = requests.get(url, headers=self._birdeye_headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success') and 'data' in data:
                price = data['data'].get('value', 0)
                self._cache_price(token_mint, price)
                
                logger.info(
                    "Token price fetched",
                    extra={
                        'token_mint': token_mint,
                        'price': price,
                        'event': 'price_fetched'
                    }
                )
                
                return price
            else:
                logger.warning(
                    "Invalid price response",
                    extra={
                        'token_mint': token_mint,
                        'response': data,
                        'event': 'invalid_price_response'
                    }
                )
                return None
                
        except Exception as e:
            logger.error(
                "Failed to fetch token price",
                extra={
                    'token_mint': token_mint,
                    'error': str(e),
                    'event': 'price_fetch_failed'
                }
            )
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_token_liquidity(self, token_mint: str) -> float:
        """Get token liquidity in USD."""
        if not self.is_available():
            logger.warning(
                "BirdEye API not configured",
                extra={'token_mint': token_mint, 'event': 'birdeye_not_configured'}
            )
            return 0.0
        
        if settings.dry_run:
            # Return mock liquidity for testing
            mock_liquidity = 10000.0 * (1 + (hash(token_mint) % 100) / 100)
            logger.info(
                "DRY RUN: Mock token liquidity",
                extra={
                    'token_mint': token_mint,
                    'liquidity': mock_liquidity,
                    'event': 'dry_run_liquidity'
                }
            )
            return mock_liquidity
        
        try:
            url = f"https://public-api.birdeye.so/defi/liquidity_pool"
            params = {"address": token_mint}
            
            response = requests.get(url, headers=self._birdeye_headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success') and 'data' in data:
                liquidity = data['data'].get('liquidity', 0)
                
                logger.info(
                    "Token liquidity fetched",
                    extra={
                        'token_mint': token_mint,
                        'liquidity': liquidity,
                        'event': 'liquidity_fetched'
                    }
                )
                
                return liquidity
            else:
                logger.warning(
                    "Invalid liquidity response",
                    extra={
                        'token_mint': token_mint,
                        'response': data,
                        'event': 'invalid_liquidity_response'
                    }
                )
                return 0.0
                
        except Exception as e:
            logger.error(
                "Failed to fetch token liquidity",
                extra={
                    'token_mint': token_mint,
                    'error': str(e),
                    'event': 'liquidity_fetch_failed'
                }
            )
            return 0.0
    
    async def get_market_cap(self, token_mint: str) -> float:
        """Get approximate market cap (liquidity * 2 for now)."""
        liquidity = await self.get_token_liquidity(token_mint)
        market_cap = liquidity * 2  # Rough approximation
        
        logger.info(
            "Market cap calculated",
            extra={
                'token_mint': token_mint,
                'liquidity': liquidity,
                'market_cap': market_cap,
                'event': 'market_cap_calculated'
            }
        )
        
        return market_cap
    
    def _get_cached_price(self, token_mint: str) -> Optional[float]:
        """Get cached price if still valid."""
        if token_mint in self._price_cache:
            cache_entry = self._price_cache[token_mint]
            if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                return cache_entry['price']
        return None
    
    def _cache_price(self, token_mint: str, price: float) -> None:
        """Cache price with timestamp."""
        self._price_cache[token_mint] = {
            'price': price,
            'timestamp': time.time()
        }
    
    def clear_cache(self) -> None:
        """Clear price cache."""
        self._price_cache.clear()
        logger.info("Price cache cleared", extra={'event': 'price_cache_cleared'})


class TrailingStop:
    """Stateful trailing stop implementation."""
    
    def __init__(self, entry_price: float, trailing_percent: float):
        self.entry_price = entry_price
        self.trailing_percent = trailing_percent
        self.peak_price = entry_price
        self.stop_price = entry_price * (1 - trailing_percent / 100)
        
        logger.info(
            "Trailing stop initialized",
            extra={
                'entry_price': entry_price,
                'trailing_percent': trailing_percent,
                'initial_stop_price': self.stop_price,
                'event': 'trailing_stop_initialized'
            }
        )
    
    def update(self, current_price: float) -> bool:
        """
        Update trailing stop with current price.
        
        Returns:
            True if stop was triggered, False otherwise
        """
        # Update peak price
        if current_price > self.peak_price:
            self.peak_price = current_price
            # Recalculate stop price
            new_stop_price = self.peak_price * (1 - self.trailing_percent / 100)
            if new_stop_price > self.stop_price:
                self.stop_price = new_stop_price
                logger.info(
                    "Trailing stop updated",
                    extra={
                        'current_price': current_price,
                        'peak_price': self.peak_price,
                        'new_stop_price': self.stop_price,
                        'event': 'trailing_stop_updated'
                    }
                )
        
        # Check if stop was triggered
        if current_price <= self.stop_price:
            logger.info(
                "Trailing stop triggered",
                extra={
                    'current_price': current_price,
                    'stop_price': self.stop_price,
                    'peak_price': self.peak_price,
                    'event': 'trailing_stop_triggered'
                }
            )
            return True
        
        return False
    
    def get_stats(self) -> dict:
        """Get trailing stop statistics."""
        return {
            'entry_price': self.entry_price,
            'peak_price': self.peak_price,
            'stop_price': self.stop_price,
            'trailing_percent': self.trailing_percent,
            'max_drawdown_from_peak': ((self.peak_price - self.stop_price) / self.peak_price) * 100
        }


# Global pricing service instance
pricing_service = PricingService()


async def get_token_price(token_mint: str) -> Optional[float]:
    """Get current token price."""
    return await pricing_service.get_token_price(token_mint)


async def get_token_liquidity(token_mint: str) -> float:
    """Get token liquidity."""
    return await pricing_service.get_token_liquidity(token_mint)


async def get_market_cap(token_mint: str) -> float:
    """Get token market cap."""
    return await pricing_service.get_market_cap(token_mint)


def create_trailing_stop(entry_price: float, trailing_percent: float) -> TrailingStop:
    """Create a new trailing stop instance."""
    return TrailingStop(entry_price, trailing_percent)


def clear_price_cache() -> None:
    """Clear price cache."""
    pricing_service.clear_cache()