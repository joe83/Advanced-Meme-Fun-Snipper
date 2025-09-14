"""Structured logging setup with correlation IDs and field redaction."""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

from .config import settings


# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging with sensitive data redaction."""
    
    SENSITIVE_FIELDS = {
        'private_key', 'api_key', 'token', 'secret', 'password', 'xai_api_key',
        'birdeye_api_key', 'telegram_token', 'mongo_uri'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with correlation ID and redaction."""
        log_data = {
            'timestamp': time.time(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': correlation_id.get(),
        }
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'exc_info', 'exc_text',
                          'stack_info', 'getMessage'):
                log_data[key] = self._redact_sensitive(key, value)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)
    
    def _redact_sensitive(self, key: str, value: Any) -> Any:
        """Redact sensitive information from log fields."""
        if isinstance(key, str) and any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
            if isinstance(value, str) and len(value) > 4:
                return f"{value[:4]}***REDACTED***"
            return "***REDACTED***"
        
        if isinstance(value, dict):
            return {k: self._redact_sensitive(k, v) for k, v in value.items()}
        
        return value


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for development."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human reading."""
        correlation = correlation_id.get()
        correlation_str = f" [{correlation[:8]}]" if correlation else ""
        
        base_msg = super().format(record)
        return f"{base_msg}{correlation_str}"


def setup_logging(level: str = "INFO", structured: bool = True) -> logging.Logger:
    """Set up structured logging with correlation ID support."""
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = HumanFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Configure third-party loggers
    logging.getLogger('websocket').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def set_correlation_id(correlation_id_value: Optional[str] = None) -> str:
    """Set correlation ID for current context."""
    if correlation_id_value is None:
        correlation_id_value = str(uuid.uuid4())
    
    correlation_id.set(correlation_id_value)
    return correlation_id_value


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id.get()


class TradeLogger:
    """Specialized logger for trade events with consistent fields."""
    
    def __init__(self, logger_name: str = "snipper.trade"):
        self.logger = get_logger(logger_name)
    
    def trade_started(self, trade_id: str, token_mint: str, analysis_score: float) -> None:
        """Log trade start event."""
        self.logger.info(
            "Trade started",
            extra={
                'event': 'trade_started',
                'trade_id': trade_id,
                'token_mint': token_mint,
                'analysis_score': analysis_score,
            }
        )
    
    def swap_executed(self, trade_id: str, tx_sig: str, side: str, 
                     amount: float, latency_ms: float) -> None:
        """Log swap execution."""
        self.logger.info(
            "Swap executed",
            extra={
                'event': 'swap_executed',
                'trade_id': trade_id,
                'tx_sig': tx_sig,
                'side': side,
                'amount': amount,
                'latency_ms': latency_ms,
            }
        )
    
    def trade_closed(self, trade_id: str, reason: str, pnl_percent: float,
                    hold_time_min: float) -> None:
        """Log trade close event."""
        self.logger.info(
            "Trade closed",
            extra={
                'event': 'trade_closed',
                'trade_id': trade_id,
                'reason': reason,
                'pnl_percent': pnl_percent,
                'hold_time_min': hold_time_min,
            }
        )
    
    def trade_error(self, trade_id: str, error_type: str, error_msg: str) -> None:
        """Log trade error."""
        self.logger.error(
            "Trade error",
            extra={
                'event': 'trade_error',
                'trade_id': trade_id,
                'error_type': error_type,
                'error_msg': error_msg,
            }
        )


# Initialize logging with settings
logger = setup_logging(
    level=settings.log_level,
    structured=True  # Always use structured logging in production
)