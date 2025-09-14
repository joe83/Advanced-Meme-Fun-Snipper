"""Logging setup module for structured logging configuration."""

import logging
import sys
from typing import Optional


def init_logging(level: str = "INFO") -> logging.Logger:
    """
    Initialize structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter for structured logging
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Create and return application logger
    app_logger = logging.getLogger("advanced_meme_fun_snipper")
    app_logger.info(f"Logging initialized at level: {level}")
    
    return app_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (defaults to 'advanced_meme_fun_snipper')
        
    Returns:
        Logger instance
    """
    if name is None:
        name = "advanced_meme_fun_snipper"
    elif not name.startswith("advanced_meme_fun_snipper"):
        name = f"advanced_meme_fun_snipper.{name}"
    
    return logging.getLogger(name)