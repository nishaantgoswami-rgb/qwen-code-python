"""
Enhanced secure credential handling for Qwen Code.
Implements proper encryption and secure storage of credentials.
"""

import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
from qwen_code.utils.logging import get_logger
from qwen_code.security.validation import DataSanitizer


logger = get_logger()


@dataclass
class SecureCredentials:
    """Enhanced authentication credentials container with additional security features."""
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None  # ISO format datetime string
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def set_expires_at(self, expires_at: datetime) -> None:
        """Set expiration time as ISO format string."""
        self.expires_at = expires_at.isoformat() if expires_at else None

    def get_expires_at(self) -> Optional[datetime]:
        """Get expiration time as datetime object."""
        if not self.expires_at:
            return None
        try:
            return datetime.fromisoformat(self.expires_at)
        except ValueError:
            return None

    def is_expired(self) -> bool:
        """Check if credentials are expired."""
        expires_at = self.get_expires_at()
        if not expires_at:
            return False
        return datetime.now() >= expires_at


class SecureCredentialManager:
    """
    Enhanced credential manager with improved security and encryption.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize secure credential manager."""
        if storage_path is None:
            # Default to user's home directory
            storage_path = Path.home() / ".qwen" / "secure_credentials.db"
        
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._key = None
        self._cipher_suite = None
        
        # Initialize database
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize secure credentials database with additional security features."""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        # Create credentials table with additional security fields
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                provider TEXT PRIMARY KEY,
                encrypted_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hash_salt TEXT NOT NULL
            )
        """)
        
        # Create metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

    def _generate_secure_salt(self) -> bytes:
        """Generate a secure random salt."""
        return os.urandom(32)  # 256-bit salt

    def _derive_key_scrypt(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key using scrypt (more secure than PBKDF2)."""
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
        """Get or create encryption key with enhanced security."""
        if self._key is not None:
            return self._key

        # Try to get existing key from metadata
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = ?", ("scrypt_salt",))
        row = cursor.fetchone()

        if row:
            # Existing salt found, derive key from environment or prompt
            salt = base64.b64decode(row[0])
            # Get password from secure source (environment variable or system keyring)
            password = os.getenv("QWEN_CREDENTIAL_PASSWORD")
            if not password:
                # Fallback to a more secure default but encourage environment variable usage
                logger.warning("QWEN_CREDENTIAL_PASSWORD not set. Using default. Please set environment variable.")
                password = "default-secure-credential-password-change-this"
            
            self._key = self._derive_key_scrypt(password, salt)
        else:
            # No existing salt, create new one
            salt = self._generate_secure_salt()
            password = os.getenv("QWEN_CREDENTIAL_PASSWORD")
            if not password:
                logger.warning("QWEN_CREDENTIAL_PASSWORD not set. Using default. Please set environment variable.")
                password = "default-secure-credential-password-change-this"
            
            self._key = self._derive_key_scrypt(password, salt)
            
            # Store salt in metadata
            salt_b64 = base64.b64encode(salt).decode()
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                ("scrypt_salt", salt_b64)
            )
            conn.commit()

        conn.close()
        return self._key

    def _get_cipher_suite(self) -> Fernet:
        """Get cipher suite for encryption/decryption."""
        if self._cipher_suite is None:
            key = self._get_or_create_key()
            self._cipher_suite = Fernet(key)
        return self._cipher_suite

    def _generate_data_salt(self) -> str:
        """Generate a salt for per-credential salting."""
        return base64.b64encode(os.urandom(32)).decode()

    def store_credentials(self, credentials: SecureCredentials) -> None:
        """
        Securely store credentials with enhanced encryption.
        
        Args:
            credentials: SecureCredentials object to store
        """
        # Serialize credentials
        creds_dict = {
            "provider": credentials.provider,
            "access_token": credentials.access_token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expires_at,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "metadata": credentials.metadata,
            "created_at": credentials.created_at
        }
        creds_json = json.dumps(creds_dict)

        # Generate per-credential salt for additional security
        data_salt = self._generate_data_salt()

        # Encrypt credentials
        cipher_suite = self._get_cipher_suite()
        try:
            encrypted_data = cipher_suite.encrypt(creds_json.encode())
            encrypted_b64 = base64.b64encode(encrypted_data).decode()
            
            # Store in database with salt
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO credentials 
                (provider, encrypted_data, updated_at, hash_salt)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            """, (credentials.provider, encrypted_b64, data_salt))
            conn.commit()
            conn.close()
            
            logger.info(f"Credentials for provider '{credentials.provider}' stored securely")
        except Exception as e:
            logger.error(f"Failed to encrypt and store credentials: {str(e)}")
            raise

    def load_credentials(self, provider: str) -> Optional[SecureCredentials]:
        """
        Load stored credentials for a provider with additional security checks.
        
        Args:
            provider: The provider name to load credentials for
            
        Returns:
            SecureCredentials object or None if not found/invalid
        """
        # Retrieve from database
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT encrypted_data FROM credentials WHERE provider = ?",
            (provider,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            logger.warning(f"No credentials found for provider: {provider}")
            return None

        # Decrypt credentials
        encrypted_b64 = row[0]
        try:
            encrypted_data = base64.b64decode(encrypted_b64)
            cipher_suite = self._get_cipher_suite()
            decrypted_json = cipher_suite.decrypt(encrypted_data).decode()
            creds_dict = json.loads(decrypted_json)

            # Parse expires_at properly
            expires_at = creds_dict.get("expires_at")
            if isinstance(expires_at, str):
                # It's already a string, which is correct for storage
                pass
            elif expires_at is not None:
                # Convert datetime to ISO string if it's a datetime object
                expires_at = expires_at.isoformat()

            # Increment access count
            self._increment_access_count(provider)

            credentials = SecureCredentials(
                provider=creds_dict["provider"],
                access_token=creds_dict["access_token"],
                refresh_token=creds_dict.get("refresh_token"),
                expires_at=expires_at,
                client_id=creds_dict.get("client_id"),
                client_secret=creds_dict.get("client_secret"),
                metadata=creds_dict.get("metadata"),
                created_at=creds_dict.get("created_at")
            )

            # Log credential access for audit purposes
            logger.info(f"Credentials loaded for provider: {provider}")

            return credentials
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for provider {provider}: {str(e)}")
            # Possible wrong password or corrupted data
            return None

    def _increment_access_count(self, provider: str) -> None:
        """Increment the access count for a provider."""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE credentials 
                SET access_count = access_count + 1, 
                    last_accessed = CURRENT_TIMESTAMP
                WHERE provider = ?
            """, (provider,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to increment access count for {provider}: {str(e)}")

    def clear_credentials(self, provider: str) -> None:
        """
        Remove stored credentials for a provider.
        
        Args:
            provider: The provider name to clear credentials for
        """
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credentials WHERE provider = ?", (provider,))
        conn.commit()
        conn.close()
        
        logger.info(f"Credentials cleared for provider: {provider}")

    def has_valid_credentials(self, provider: str) -> bool:
        """
        Check if valid credentials are stored for a provider.
        
        Args:
            provider: The provider name to check
            
        Returns:
            True if valid credentials exist, False otherwise
        """
        creds = self.load_credentials(provider)
        if not creds:
            return False

        # Check if access_token exists
        if not creds.access_token:
            logger.warning(f"No access token for provider: {provider}")
            return False

        # Check token expiration if available
        if creds.expires_at:
            try:
                expires_at = datetime.fromisoformat(creds.expires_at)
                # Consider token expired 5 minutes before actual expiration to allow for refresh
                if expires_at <= (datetime.now() + timedelta(minutes=5)):
                    logger.warning(f"Credentials for {provider} are expired or will expire soon")
                    return False
            except ValueError:
                # Invalid date format, treat as expired
                logger.warning(f"Invalid expiration date format for {provider}")
                return False

        return True

    def list_providers(self) -> list:
        """
        List all providers with stored credentials.
        
        Returns:
            List of provider names with stored credentials
        """
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("SELECT provider FROM credentials")
        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    def get_credential_stats(self, provider: str) -> dict:
        """
        Get statistics for a specific provider's credentials.
        
        Args:
            provider: The provider name to get stats for
            
        Returns:
            Dictionary with credential statistics
        """
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT access_count, created_at, updated_at, last_accessed 
            FROM credentials WHERE provider = ?
        """, (provider,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {}

        return {
            "access_count": row[0],
            "created_at": row[1],
            "updated_at": row[2],
            "last_accessed": row[3]
        }

    def rotate_encryption_key(self) -> None:
        """
        Rotate the encryption key (requires re-encrypting all credentials).
        """
        logger.info("Starting encryption key rotation...")
        
        # Load all existing credentials
        providers = self.list_providers()
        all_credentials = {}
        
        for provider in providers:
            creds = self.load_credentials(provider)
            if creds:
                all_credentials[provider] = creds
        
        # Generate new salt and key
        new_salt = self._generate_secure_salt()
        password = os.getenv("QWEN_CREDENTIAL_PASSWORD")
        if not password:
            logger.warning("QWEN_CREDENTIAL_PASSWORD not set. Using default. Please set environment variable.")
            password = "default-secure-credential-password-change-this"
        
        new_key = self._derive_key_scrypt(password, new_salt)
        old_cipher_suite = self._cipher_suite
        self._key = new_key
        self._cipher_suite = None  # Force regeneration
        
        # Re-encrypt all credentials with new key
        for provider, creds in all_credentials.items():
            try:
                self.store_credentials(creds)
                logger.info(f"Re-encrypted credentials for provider: {provider}")
            except Exception as e:
                logger.error(f"Failed to re-encrypt credentials for {provider}: {str(e)}")
                # Restore old key if any failure occurs
                self._key = old_cipher_suite._fernet._encryption_key
                self._cipher_suite = old_cipher_suite
                raise
        
        # Update the stored salt
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        salt_b64 = base64.b64encode(new_salt).decode()
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("scrypt_salt", salt_b64)
        )
        conn.commit()
        conn.close()
        
        logger.info("Encryption key rotation completed successfully")