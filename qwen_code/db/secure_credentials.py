"""
Secure credential service that combines database encryption with secure credential management.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from qwen_code.db.models import AuthToken
from qwen_code.security.credentials import SecureCredentialManager, SecureCredentials
from qwen_code.db.encryption import EncryptionManager
from qwen_code.utils.logging import get_logger
from sqlalchemy.orm import Session


logger = get_logger()


class SecureCredentialService:
    """
    Service for handling secure credential storage with both database encryption
    and credential management from the existing system.
    """
    
    def __init__(self):
        self.encryption_manager = EncryptionManager()
        self.credential_manager = SecureCredentialManager()
        
    def store_token_encrypted(self, db_session: Session, provider: str, access_token: str, 
                             refresh_token: Optional[str] = None, expires_at: Optional[datetime] = None) -> None:
        """
        Store authentication token with encryption in the database.
        
        Args:
            db_session: SQLAlchemy database session
            provider: The provider name
            access_token: The access token to store
            refresh_token: The refresh token to store (optional)
            expires_at: Expiration datetime (optional)
        """
        try:
            # Encrypt tokens before storing
            encrypted_access_token = self.encryption_manager.encrypt_data(access_token)
            encrypted_refresh_token = self.encryption_manager.encrypt_data(refresh_token) if refresh_token else None
            
            # Check if token already exists
            existing_token = db_session.query(AuthToken).filter(AuthToken.provider == provider).first()
            
            if existing_token:
                # Update existing token
                existing_token.encrypted_access_token = encrypted_access_token
                existing_token.encrypted_refresh_token = encrypted_refresh_token
                existing_token.expires_at = expires_at
                existing_token.updated_at = datetime.utcnow()
            else:
                # Create new token
                token = AuthToken(
                    provider=provider,
                    encrypted_access_token=encrypted_access_token,
                    encrypted_refresh_token=encrypted_refresh_token,
                    expires_at=expires_at
                )
                db_session.add(token)
            
            db_session.commit()
            logger.info(f"Encrypted token stored for provider: {provider}")
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to store encrypted token for provider {provider}: {str(e)}")
            raise
    
    def get_token_decrypted(self, db_session: Session, provider: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt authentication token from the database.
        
        Args:
            db_session: SQLAlchemy database session
            provider: The provider name
            
        Returns:
            Dictionary with token information or None if not found
        """
        try:
            token = db_session.query(AuthToken).filter(AuthToken.provider == provider).first()
            
            if not token:
                logger.warning(f"No token found for provider: {provider}")
                return None
            
            # Decrypt tokens
            decrypted_access_token = self.encryption_manager.decrypt_data(token.encrypted_access_token)
            decrypted_refresh_token = None
            if token.encrypted_refresh_token:
                decrypted_refresh_token = self.encryption_manager.decrypt_data(token.encrypted_refresh_token)
            
            return {
                "provider": token.provider,
                "access_token": decrypted_access_token,
                "refresh_token": decrypted_refresh_token,
                "expires_at": token.expires_at,
                "created_at": token.created_at,
                "updated_at": token.updated_at
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve and decrypt token for provider {provider}: {str(e)}")
            return None
    
    def delete_token(self, db_session: Session, provider: str) -> bool:
        """
        Delete authentication token from the database.
        
        Args:
            db_session: SQLAlchemy database session
            provider: The provider name
            
        Returns:
            True if token was deleted, False otherwise
        """
        try:
            token = db_session.query(AuthToken).filter(AuthToken.provider == provider).first()
            
            if token:
                db_session.delete(token)
                db_session.commit()
                logger.info(f"Token deleted for provider: {provider}")
                return True
            else:
                logger.warning(f"No token found to delete for provider: {provider}")
                return False
                
        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to delete token for provider {provider}: {str(e)}")
            return False
    
    def is_token_expired(self, token_data: Dict[str, Any]) -> bool:
        """
        Check if the token is expired.
        
        Args:
            token_data: Dictionary with token information including expires_at
            
        Returns:
            True if token is expired, False otherwise
        """
        expires_at = token_data.get("expires_at")
        if not expires_at:
            return False
            
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                return True  # Invalid date format is treated as expired
                
        return datetime.utcnow() >= expires_at