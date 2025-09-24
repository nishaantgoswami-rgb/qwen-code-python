"""
Credential management with encryption for Qwen Code.
"""

import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path
import sqlite3
from datetime import datetime


@dataclass
class Credentials:
    """Authentication credentials container."""
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None  # ISO format datetime string
    metadata: Optional[Dict[str, Any]] = None
    client_id: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
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


class CredentialManager:
    """Manages secure storage and retrieval of credentials."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize credential manager."""
        if storage_path is None:
            # Default to user's home directory
            storage_path = Path.home() / ".qwen" / "credentials.db"
        
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._key = None
        self._cipher_suite = None
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize credentials database."""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        # Create credentials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                provider TEXT PRIMARY KEY,
                encrypted_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key."""
        if self._key is not None:
            return self._key
        
        # Try to get existing key from metadata
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = ?", ("salt",))
        row = cursor.fetchone()
        
        if row:
            # Existing salt found, derive key from environment or prompt
            salt = base64.b64decode(row[0])
            password = os.getenv("QWEN_CREDENTIAL_PASSWORD", "default-password")
            self._key = self._derive_key(password, salt)
        else:
            # No existing salt, create new one
            salt = os.urandom(16)
            password = os.getenv("QWEN_CREDENTIAL_PASSWORD", "default-password")
            self._key = self._derive_key(password, salt)
            
            # Store salt in metadata
            salt_b64 = base64.b64encode(salt).decode()
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                ("salt", salt_b64)
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
    
    def store_credentials(self, credentials: Credentials) -> None:
        """Securely store credentials."""
        # Serialize credentials
        creds_dict = {
            "provider": credentials.provider,
            "access_token": credentials.access_token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expires_at,  # Already a string from the dataclass
            "metadata": credentials.metadata,
            "client_id": credentials.client_id
        }
        creds_json = json.dumps(creds_dict)
        
        # Encrypt credentials
        cipher_suite = self._get_cipher_suite()
        encrypted_data = cipher_suite.encrypt(creds_json.encode())
        encrypted_b64 = base64.b64encode(encrypted_data).decode()
        
        # Store in database
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO credentials 
            (provider, encrypted_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (credentials.provider, encrypted_b64))
        conn.commit()
        conn.close()
    
    def load_credentials(self, provider: str) -> Optional[Credentials]:
        """Load stored credentials for a provider."""
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
            return None
        
        # Decrypt credentials
        encrypted_b64 = row[0]
        encrypted_data = base64.b64decode(encrypted_b64)
        cipher_suite = self._get_cipher_suite()
        try:
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
            
            return Credentials(
                provider=creds_dict["provider"],
                access_token=creds_dict["access_token"],
                refresh_token=creds_dict.get("refresh_token"),
                expires_at=expires_at,
                metadata=creds_dict.get("metadata"),
                client_id=creds_dict.get("client_id")
            )
        except Exception:
            # Decryption failed, possibly due to wrong password
            return None
    
    def clear_credentials(self, provider: str) -> None:
        """Remove stored credentials for a provider."""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credentials WHERE provider = ?", (provider,))
        conn.commit()
        conn.close()
    
    def has_valid_credentials(self, provider: str) -> bool:
        """Check if valid credentials are stored for a provider."""
        creds = self.load_credentials(provider)
        if not creds:
            return False
        
        # Check if access_token exists
        if not creds.access_token:
            return False
        
        # Check token expiration if available
        if creds.expires_at:
            from datetime import datetime, timedelta
            try:
                expires_at = datetime.fromisoformat(creds.expires_at)
                # Consider token expired 5 minutes before actual expiration to allow for refresh
                if expires_at <= (datetime.now() + timedelta(minutes=5)):
                    return False
            except ValueError:
                # Invalid date format, treat as expired
                return False
        
        return True
    
    def list_providers(self) -> list:
        """List all providers with stored credentials."""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("SELECT provider FROM credentials")
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    
    def save_tokens_to_json(self, tokens: dict, json_path: Optional[Path] = None) -> None:
        """Save tokens to JSON file (matching the example implementation)."""
        if json_path is None:
            json_path = Path.home() / ".qwen" / "credential_manager_creds.json"
        
        # Create directory if it doesn't exist
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save tokens to JSON file
        with open(json_path, 'w') as f:
            json.dump(tokens, f)
    
    def load_tokens_from_json(self, json_path: Optional[Path] = None) -> dict:
        """Load tokens from JSON file (matching the example implementation)."""
        if json_path is None:
            json_path = Path.home() / ".qwen" / "credential_manager_creds.json"
        
        # Check if file exists
        if not json_path.exists():
            return {}
        
        # Load tokens from JSON file
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}