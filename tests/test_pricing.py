"""Tests for pricing service and trailing stop."""

import pytest
from unittest.mock import AsyncMock, patch

from snipper.services.pricing import PricingService, TrailingStop


class TestTrailingStop:
    """Test TrailingStop functionality."""
    
    def test_trailing_stop_initialization(self):
        """Test trailing stop initialization."""
        trailing_stop = TrailingStop(entry_price=1.0, trailing_percent=10.0)
        
        assert trailing_stop.entry_price == 1.0
        assert trailing_stop.trailing_percent == 10.0
        assert trailing_stop.peak_price == 1.0
        assert trailing_stop.stop_price == 0.9  # 1.0 * (1 - 10/100)
    
    def test_trailing_stop_update_higher_price(self):
        """Test trailing stop update with higher price."""
        trailing_stop = TrailingStop(entry_price=1.0, trailing_percent=10.0)
        
        # Price goes up
        triggered = trailing_stop.update(1.2)
        assert triggered is False
        assert trailing_stop.peak_price == 1.2
        assert trailing_stop.stop_price == 1.08  # 1.2 * (1 - 10/100)
        
        # Price goes up more
        triggered = trailing_stop.update(1.5)
        assert triggered is False
        assert trailing_stop.peak_price == 1.5
        assert trailing_stop.stop_price == 1.35  # 1.5 * (1 - 10/100)
    
    def test_trailing_stop_update_lower_price(self):
        """Test trailing stop update with lower price (no trigger)."""
        trailing_stop = TrailingStop(entry_price=1.0, trailing_percent=10.0)
        
        # Set a higher peak first
        trailing_stop.update(1.2)
        
        # Price drops but not below stop
        triggered = trailing_stop.update(1.1)
        assert triggered is False
        assert trailing_stop.peak_price == 1.2  # Unchanged
        assert trailing_stop.stop_price == 1.08  # Unchanged
    
    def test_trailing_stop_triggered(self):
        """Test trailing stop trigger."""
        trailing_stop = TrailingStop(entry_price=1.0, trailing_percent=10.0)
        
        # Set a higher peak
        trailing_stop.update(1.2)  # Stop at 1.08
        
        # Price drops below stop
        triggered = trailing_stop.update(1.05)
        assert triggered is True
    
    def test_trailing_stop_stats(self):
        """Test trailing stop statistics."""
        trailing_stop = TrailingStop(entry_price=1.0, trailing_percent=10.0)
        trailing_stop.update(1.5)  # Peak at 1.5, stop at 1.35
        
        stats = trailing_stop.get_stats()
        
        assert stats['entry_price'] == 1.0
        assert stats['peak_price'] == 1.5
        assert stats['stop_price'] == 1.35
        assert stats['trailing_percent'] == 10.0
        assert stats['max_drawdown_from_peak'] == 10.0


class TestPricingService:
    """Test PricingService functionality."""
    
    def test_pricing_service_initialization(self):
        """Test pricing service initialization."""
        service = PricingService()
        
        assert service._cache_ttl == 5.0
        assert len(service._price_cache) == 0
    
    def test_is_available(self):
        """Test availability check."""
        service = PricingService()
        
        # Mock settings to have birdeye API key
        with patch('snipper.services.pricing.settings') as mock_settings:
            mock_settings.birdeye_api_key = "test_key"
            assert service.is_available() is True
            
            mock_settings.birdeye_api_key = None
            assert service.is_available() is False
    
    @pytest.mark.asyncio
    async def test_get_token_price_dry_run(self):
        """Test token price retrieval in dry run mode."""
        service = PricingService()
        
        with patch('snipper.services.pricing.settings') as mock_settings:
            mock_settings.dry_run = True
            mock_settings.birdeye_api_key = "test_key"
            
            price = await service.get_token_price("test_mint")
            assert price is not None
            assert isinstance(price, float)
            assert price > 0
    
    @pytest.mark.asyncio
    async def test_get_token_price_not_available(self):
        """Test token price retrieval when service not available."""
        service = PricingService()
        
        with patch('snipper.services.pricing.settings') as mock_settings:
            mock_settings.birdeye_api_key = None
            
            price = await service.get_token_price("test_mint")
            assert price is None
    
    @pytest.mark.asyncio
    async def test_get_token_liquidity_dry_run(self):
        """Test token liquidity retrieval in dry run mode."""
        service = PricingService()
        
        with patch('snipper.services.pricing.settings') as mock_settings:
            mock_settings.dry_run = True
            mock_settings.birdeye_api_key = "test_key"
            
            liquidity = await service.get_token_liquidity("test_mint")
            assert isinstance(liquidity, float)
            assert liquidity > 0
    
    @pytest.mark.asyncio
    async def test_get_market_cap(self):
        """Test market cap calculation."""
        service = PricingService()
        
        with patch.object(service, 'get_token_liquidity', return_value=10000.0):
            market_cap = await service.get_market_cap("test_mint")
            assert market_cap == 20000.0  # liquidity * 2
    
    def test_price_caching(self):
        """Test price caching functionality."""
        service = PricingService()
        
        # Cache a price
        service._cache_price("test_mint", 1.5)
        
        # Should get cached price
        cached_price = service._get_cached_price("test_mint")
        assert cached_price == 1.5
        
        # Clear cache
        service.clear_cache()
        assert len(service._price_cache) == 0
        
        # Should not get cached price after clear
        cached_price = service._get_cached_price("test_mint")
        assert cached_price is None
    
    def test_cache_expiration(self):
        """Test cache expiration."""
        service = PricingService()
        service._cache_ttl = 0.01  # Very short TTL for testing
        
        # Cache a price
        service._cache_price("test_mint", 1.5)
        
        # Should get cached price immediately
        cached_price = service._get_cached_price("test_mint")
        assert cached_price == 1.5
        
        # Wait for expiration
        import time
        time.sleep(0.02)
        
        # Should not get cached price after expiration
        cached_price = service._get_cached_price("test_mint")
        assert cached_price is None


class TestPricingServiceMocking:
    """Test pricing service with mocked HTTP requests."""
    
    @pytest.mark.asyncio
    async def test_successful_api_response(self):
        """Test successful API response handling."""
        service = PricingService()
        
        mock_response = {
            'success': True,
            'data': {'value': 0.123456}
        }
        
        with patch('snipper.services.pricing.settings') as mock_settings, \
             patch('snippet.services.pricing.requests.get') as mock_get:
            
            mock_settings.birdeye_api_key = "test_key"
            mock_settings.dry_run = False
            
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status.return_value = None
            
            price = await service.get_token_price("test_mint")
            assert price == 0.123456
    
    @pytest.mark.asyncio
    async def test_failed_api_response(self):
        """Test failed API response handling."""
        service = PricingService()
        
        mock_response = {
            'success': False,
            'data': {}
        }
        
        with patch('snipper.services.pricing.settings') as mock_settings, \
             patch('snipper.services.pricing.requests.get') as mock_get:
            
            mock_settings.birdeye_api_key = "test_key"
            mock_settings.dry_run = False
            
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status.return_value = None
            
            price = await service.get_token_price("test_mint")
            assert price is None