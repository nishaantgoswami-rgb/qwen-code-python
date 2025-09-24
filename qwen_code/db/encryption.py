"""
Encryption utilities for secure data storage in Qwen Code.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from qwen_code.utils.logging import get_logger
import json


logger = get_logger()


class EncryptionManager:
    """
    Secure encryption manager for sensitive data storage.
    """
    
    def __init__(self):
        self._key = None
        self._cipher_suite = None
        
    def _generate_secure_salt(self) -> bytes:
        """Generate a secure random salt for key derivation."""
        return os.urandom(32)  # 256-bit salt
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key using scrypt for secure key derivation."""
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=2**14,  # 16384 - computational cost parameter
            r=8,      # Block size parameter
            p=1,      # Parallelization parameter
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key with proper security handling."""
        if self._key is not None:
            return self._key
        
        # Get password from environment variable
        password = os.getenv("QWEN_DB_PASSWORD")
        if not password:
            # Log a warning but try to use a default for development
            logger.warning("QWEN_DB_PASSWORD environment variable not set. Using default for development. Please set environment variable for production.")
            password = "default-secure-db-password-change-this"
        
        # For now, we'll use a simple salt approach - in production, 
        # the salt should be securely stored separately
        salt = self._generate_secure_salt()
        self._key = self._derive_key(password, salt)
        return self._key
    
    def _get_cipher_suite(self) -> Fernet:
        """Get cipher suite for encryption/decryption operations."""
        if self._cipher_suite is None:
            key = self._get_or_create_key()
            self._cipher_suite = Fernet(key)
        return self._cipher_suite
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt data and return as base64 string."""
        try:
            cipher_suite = self._get_cipher_suite()
            encrypted_bytes = cipher_suite.encrypt(data.encode())
            return base64.b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data and return original string."""
        try:
            cipher_suite = self._get_cipher_suite()
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_bytes = cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
    
    def encrypt_json(self, data: dict) -> str:
        """Encrypt JSON data for storage."""
        json_str = json.dumps(data)
        return self.encrypt_data(json_str)
    
    def decrypt_json(self, encrypted_data: str) -> dict:
        """Decrypt JSON data from storage."""
        json_str = self.decrypt_data(encrypted_data)
        return json.loads(json_str)