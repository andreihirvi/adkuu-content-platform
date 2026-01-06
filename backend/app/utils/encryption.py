"""
Encryption utilities for securing sensitive data like OAuth tokens.
"""
import base64
import os
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.

    Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
    """

    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryption service.

        Args:
            key: Base64-encoded Fernet key. If not provided, uses settings.
        """
        if key:
            self._key = key.encode() if isinstance(key, str) else key
        elif settings.ENCRYPTION_KEY:
            self._key = settings.ENCRYPTION_KEY.encode()
        else:
            # Generate a key if none provided (not recommended for production)
            self._key = Fernet.generate_key()

        try:
            self._fernet = Fernet(self._key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.

        Args:
            data: Plain text string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not data:
            return ""

        encrypted = self._fernet.encrypt(data.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted_data: Base64-encoded encrypted string

        Returns:
            Decrypted plain text string

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_data:
            return ""

        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted = self._fernet.decrypt(decoded)
            return decrypted.decode('utf-8')
        except InvalidToken:
            raise ValueError("Failed to decrypt: invalid token or wrong key")
        except Exception as e:
            raise ValueError(f"Failed to decrypt: {e}")

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded key string
        """
        return Fernet.generate_key().decode('utf-8')


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_token(token: str) -> str:
    """
    Encrypt an OAuth token.

    Args:
        token: Plain text token

    Returns:
        Encrypted token string
    """
    return get_encryption_service().encrypt(token)


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt an OAuth token.

    Args:
        encrypted_token: Encrypted token string

    Returns:
        Plain text token
    """
    return get_encryption_service().decrypt(encrypted_token)
