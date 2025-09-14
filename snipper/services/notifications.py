"""Notification service with pluggable channels."""

from abc import ABC, abstractmethod
from typing import Optional

from telegram import Bot
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""
    
    @abstractmethod
    async def send_message(self, message: str) -> bool:
        """Send a notification message."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the notification channel is available."""
        pass


class TelegramChannel(NotificationChannel):
    """Telegram notification channel."""
    
    def __init__(self):
        self._bot: Optional[Bot] = None
        self._channel = settings.telegram_channel
    
    @property
    def bot(self) -> Optional[Bot]:
        """Get Telegram bot instance."""
        if not self._bot and settings.telegram_token and self._channel:
            self._bot = Bot(token=settings.telegram_token)
        return self._bot
    
    def is_available(self) -> bool:
        """Check if Telegram is configured and available."""
        return bool(settings.telegram_token and self._channel)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def send_message(self, message: str) -> bool:
        """Send message via Telegram."""
        if not self.is_available():
            logger.warning("Telegram not configured", extra={'event': 'telegram_not_configured'})
            return False
        
        if settings.dry_run:
            logger.info(
                "DRY RUN: Would send Telegram message",
                extra={
                    'message': message[:100] + "..." if len(message) > 100 else message,
                    'channel': self._channel,
                    'event': 'dry_run_telegram'
                }
            )
            return True
        
        try:
            bot = self.bot
            if not bot:
                return False
            
            # Truncate message if too long (Telegram limit is 4096 characters)
            if len(message) > 4000:
                message = message[:4000] + "... (truncated)"
            
            await bot.send_message(chat_id=self._channel, text=message)
            
            logger.info(
                "Telegram message sent",
                extra={
                    'channel': self._channel,
                    'message_length': len(message),
                    'event': 'telegram_sent'
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to send Telegram message",
                extra={
                    'channel': self._channel,
                    'error': str(e),
                    'event': 'telegram_failed'
                }
            )
            return False


class SlackChannel(NotificationChannel):
    """Slack notification channel (placeholder for future implementation)."""
    
    def is_available(self) -> bool:
        """Check if Slack is configured."""
        return False  # Not implemented yet
    
    async def send_message(self, message: str) -> bool:
        """Send message via Slack (placeholder)."""
        logger.warning("Slack channel not implemented", extra={'event': 'slack_not_implemented'})
        return False


class WebhookChannel(NotificationChannel):
    """Webhook notification channel (placeholder for future implementation)."""
    
    def is_available(self) -> bool:
        """Check if webhook is configured."""
        return False  # Not implemented yet
    
    async def send_message(self, message: str) -> bool:
        """Send message via webhook (placeholder)."""
        logger.warning("Webhook channel not implemented", extra={'event': 'webhook_not_implemented'})
        return False


class NotificationService:
    """Unified notification service supporting multiple channels."""
    
    def __init__(self):
        self.channels = {
            'telegram': TelegramChannel(),
            'slack': SlackChannel(),
            'webhook': WebhookChannel(),
        }
    
    def get_available_channels(self) -> list[str]:
        """Get list of available notification channels."""
        return [name for name, channel in self.channels.items() if channel.is_available()]
    
    async def send_notification(self, message: str, channels: Optional[list[str]] = None) -> dict[str, bool]:
        """Send notification to specified channels or all available channels."""
        if channels is None:
            channels = self.get_available_channels()
        
        if not channels:
            logger.warning(
                "No notification channels available",
                extra={'event': 'no_channels_available'}
            )
            return {}
        
        results = {}
        for channel_name in channels:
            if channel_name in self.channels:
                channel = self.channels[channel_name]
                if channel.is_available():
                    try:
                        success = await channel.send_message(message)
                        results[channel_name] = success
                    except Exception as e:
                        logger.error(
                            f"Failed to send notification via {channel_name}",
                            extra={
                                'channel': channel_name,
                                'error': str(e),
                                'event': 'notification_failed'
                            }
                        )
                        results[channel_name] = False
                else:
                    logger.warning(
                        f"Channel {channel_name} not available",
                        extra={
                            'channel': channel_name,
                            'event': 'channel_not_available'
                        }
                    )
                    results[channel_name] = False
            else:
                logger.warning(
                    f"Unknown channel {channel_name}",
                    extra={
                        'channel': channel_name,
                        'event': 'unknown_channel'
                    }
                )
                results[channel_name] = False
        
        return results
    
    async def send_trade_alert(self, trade_id: str, message: str) -> bool:
        """Send trade-specific alert with trade ID context."""
        formatted_message = f"[Trade {trade_id[:8]}] {message}"
        results = await self.send_notification(formatted_message)
        
        success = any(results.values())
        logger.info(
            "Trade alert sent",
            extra={
                'trade_id': trade_id,
                'success': success,
                'channels': list(results.keys()),
                'event': 'trade_alert_sent'
            }
        )
        
        return success
    
    async def send_system_alert(self, message: str) -> bool:
        """Send system-level alert."""
        formatted_message = f"[SYSTEM] {message}"
        results = await self.send_notification(formatted_message)
        
        success = any(results.values())
        logger.info(
            "System alert sent",
            extra={
                'success': success,
                'channels': list(results.keys()),
                'event': 'system_alert_sent'
            }
        )
        
        return success
    
    async def send_error_alert(self, error_type: str, error_message: str) -> bool:
        """Send error alert."""
        formatted_message = f"[ERROR] {error_type}: {error_message}"
        results = await self.send_notification(formatted_message)
        
        success = any(results.values())
        logger.error(
            "Error alert sent",
            extra={
                'error_type': error_type,
                'success': success,
                'channels': list(results.keys()),
                'event': 'error_alert_sent'
            }
        )
        
        return success


# Global notification service instance
notification_service = NotificationService()


async def send_notification(message: str, channels: Optional[list[str]] = None) -> dict[str, bool]:
    """Send notification via available channels."""
    return await notification_service.send_notification(message, channels)


async def send_trade_alert(trade_id: str, message: str) -> bool:
    """Send trade-specific alert."""
    return await notification_service.send_trade_alert(trade_id, message)


async def send_system_alert(message: str) -> bool:
    """Send system-level alert."""
    return await notification_service.send_system_alert(message)


async def send_error_alert(error_type: str, error_message: str) -> bool:
    """Send error alert."""
    return await notification_service.send_error_alert(error_type, error_message)