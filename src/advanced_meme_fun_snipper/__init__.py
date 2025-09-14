"""Advanced Meme Fun Snipper - A production-ready Solana meme coin sniping bot."""

__version__ = "0.1.0"


def get_version() -> str:
    """Return the package version."""
    return __version__


# Re-export main components for easy importing
from .logging_setup import init_logging

__all__ = ["get_version", "init_logging"]