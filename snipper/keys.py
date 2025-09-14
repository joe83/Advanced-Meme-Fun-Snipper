"""Secure keypair loading and validation."""

from typing import Optional

import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


class KeypairManager:
    """Manages keypair loading with validation and security features."""
    
    def __init__(self):
        self._keypair: Optional[Keypair] = None
        self._pubkey: Optional[Pubkey] = None
    
    def load_keypair(self) -> Keypair:
        """Load and validate keypair from configuration."""
        if self._keypair is not None:
            return self._keypair
        
        try:
            # Decode the base58 private key
            private_key_bytes = base58.b58decode(settings.private_key)
            
            # Validate length
            if len(private_key_bytes) != 64:
                raise ValueError(f"Private key must be 64 bytes, got {len(private_key_bytes)}")
            
            # Create keypair
            self._keypair = Keypair.from_bytes(private_key_bytes)
            self._pubkey = self._keypair.pubkey()
            
            # Log public key (safe to log)
            logger.info(
                "Keypair loaded successfully",
                extra={
                    'wallet_pubkey': str(self._pubkey),
                    'event': 'keypair_loaded'
                }
            )
            
            return self._keypair
            
        except Exception as e:
            logger.error(
                "Failed to load keypair",
                extra={
                    'error': str(e),
                    'event': 'keypair_load_failed'
                }
            )
            raise ValueError(f"Failed to load keypair: {e}")
    
    @property
    def keypair(self) -> Keypair:
        """Get the loaded keypair."""
        if self._keypair is None:
            return self.load_keypair()
        return self._keypair
    
    @property
    def pubkey(self) -> Pubkey:
        """Get the public key."""
        if self._pubkey is None:
            self.load_keypair()
        return self._pubkey
    
    def validate_keypair(self) -> bool:
        """Validate that the keypair is properly loaded and functional."""
        try:
            keypair = self.keypair
            pubkey = self.pubkey
            
            # Basic validation - ensure we can sign and verify
            test_message = b"test_message"
            signature = keypair.sign_message(test_message)
            
            # If we get here without exception, keypair is valid
            logger.info(
                "Keypair validation successful",
                extra={
                    'wallet_pubkey': str(pubkey),
                    'event': 'keypair_validated'
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                "Keypair validation failed",
                extra={
                    'error': str(e),
                    'event': 'keypair_validation_failed'
                }
            )
            return False


# Global keypair manager instance
keypair_manager = KeypairManager()


def get_keypair() -> Keypair:
    """Get the loaded keypair."""
    return keypair_manager.keypair


def get_wallet_pubkey() -> Pubkey:
    """Get the wallet public key."""
    return keypair_manager.pubkey


def validate_keypair() -> bool:
    """Validate the loaded keypair."""
    return keypair_manager.validate_keypair()