"""
DashScope token exchange mechanism for converting Qwen OAuth tokens to DashScope API keys.

This module handles the process of exchanging OAuth tokens obtained from Qwen's OAuth flow
for DashScope API keys that can be used with the DashScope compatible API endpoint.

The exchange process:
1. Takes a Qwen OAuth token
2. Sends it to the DashScope token exchange endpoint
3. Receives a DashScope API key in response
4. Caches the API key for future use

The implementation follows the API specification with proper endpoints and parameters.
"""

import json
import time
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import httpx

# DashScope token exchange endpoint (based on API specification)
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"
DASHSCOPE_TOKEN_EXCHANGE_URL = f"{DASHSCOPE_BASE_URL}/compatible-mode/v1/apikey"

# Cache file for DashScope API keys
DASHSCOPE_CACHE_FILE = Path.home() / ".qwen" / "dashscope_api_keys.json"


def _save_dashscope_creds(creds: Dict[str, Any]) -> None:
    """Save DashScope credentials to JSON file."""
    DASHSCOPE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DASHSCOPE_CACHE_FILE, 'w') as f:
        json.dump(creds, f)


def _load_dashscope_creds() -> Optional[Dict[str, Any]]:
    """Load DashScope credentials from JSON file."""
    if DASHSCOPE_CACHE_FILE.exists():
        try:
            with open(DASHSCOPE_CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


class DashScopeTokenExchange:
    """Handles token exchange from Qwen OAuth tokens to DashScope API keys."""
    
    @staticmethod
    async def exchange_token(oauth_token: str) -> Optional[str]:
        """
        Exchange Qwen OAuth token for DashScope API key.
        
        Args:
            oauth_token: The Qwen OAuth token to exchange
            
        Returns:
            DashScope API key if successful, None otherwise
        """
        # Check cache first
        cached_key = DashScopeTokenExchange._get_cached_api_key()
        if cached_key:
            return cached_key
            
        # Use the proper endpoint as defined in the API documentation
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # First try the compatible-mode API key exchange endpoint
                response = await client.post(
                    DASHSCOPE_TOKEN_EXCHANGE_URL,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Different APIs might return the key in different fields
                    api_key = (data.get("api_key") or 
                              data.get("apikey") or 
                              data.get("key") or 
                              data.get("data", {}).get("api_key"))
                    
                    if api_key:
                        expires_in = data.get("expires_in", 3600)  # Default to 1 hour
                        # Cache the API key
                        DashScopeTokenExchange._cache_api_key(api_key, expires_in)
                        return api_key
                
                # If POST fails, try alternative endpoints based on API spec
                # Try Qwen API endpoint for user API keys
                alt_url = "https://chat.qwen.ai/api/v1/user/apikeys"
                response = await client.get(
                    alt_url,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Different APIs might return the key in different fields
                    api_key = (data.get("api_key") or 
                              data.get("apikey") or 
                              data.get("key") or 
                              data.get("data", {}).get("api_key") or
                              # Handle list of API keys
                              (data.get("data", [{}])[0] if isinstance(data.get("data"), list) and data["data"] else {}).get("api_key"))
                    
                    if api_key:
                        expires_in = data.get("expires_in", 3600)  # Default to 1 hour
                        # Cache the API key
                        DashScopeTokenExchange._cache_api_key(api_key, expires_in)
                        return api_key
                        
                # If both fail, return None
                return None
                
        except httpx.RequestError as e:
            # Network error occurred
            print(f"Error during token exchange: {e}")
            return None
        except Exception as e:
            # Other error occurred
            print(f"Unexpected error during token exchange: {e}")
            return None
    
    @staticmethod
    def exchange_token_sync(oauth_token: str) -> Optional[str]:
        """
        Synchronously exchange Qwen OAuth token for DashScope API key.
        
        Args:
            oauth_token: The Qwen OAuth token to exchange
            
        Returns:
            DashScope API key if successful, None otherwise
        """
        # Check cache first
        cached_key = DashScopeTokenExchange._get_cached_api_key()
        if cached_key:
            return cached_key
            
        # Use the proper endpoint as defined in the API documentation
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        try:
            with httpx.Client() as client:
                # First try the compatible-mode API key exchange endpoint
                response = client.post(
                    DASHSCOPE_TOKEN_EXCHANGE_URL,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Different APIs might return the key in different fields
                    api_key = (data.get("api_key") or 
                              data.get("apikey") or 
                              data.get("key") or 
                              data.get("data", {}).get("api_key"))
                    
                    if api_key:
                        expires_in = data.get("expires_in", 3600)  # Default to 1 hour
                        # Cache the API key
                        DashScopeTokenExchange._cache_api_key(api_key, expires_in)
                        return api_key
                
                # If POST fails, try alternative endpoints based on API spec
                # Try Qwen API endpoint for user API keys
                alt_url = "https://chat.qwen.ai/api/v1/user/apikeys"
                response = client.get(
                    alt_url,
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Different APIs might return the key in different fields
                    api_key = (data.get("api_key") or 
                              data.get("apikey") or 
                              data.get("key") or 
                              data.get("data", {}).get("api_key") or
                              # Handle list of API keys
                              (data.get("data", [{}])[0] if isinstance(data.get("data"), list) and data["data"] else {}).get("api_key"))
                    
                    if api_key:
                        expires_in = data.get("expires_in", 3600)  # Default to 1 hour
                        # Cache the API key
                        DashScopeTokenExchange._cache_api_key(api_key, expires_in)
                        return api_key
                        
                # If both fail, return None
                return None
                
        except httpx.RequestError as e:
            # Network error occurred
            print(f"Error during token exchange: {e}")
            return None
        except Exception as e:
            # Other error occurred
            print(f"Unexpected error during token exchange: {e}")
            return None
    
    @staticmethod
    def _cache_api_key(api_key: str, expires_in: int) -> None:
        """Cache the DashScope API key with expiration."""
        expiry_time = datetime.now() + timedelta(seconds=expires_in)
        creds = {
            "api_key": api_key,
            "expires_at": expiry_time.isoformat()
        }
        _save_dashscope_creds(creds)
    
    @staticmethod
    def _get_cached_api_key() -> Optional[str]:
        """Get cached DashScope API key if still valid."""
        creds = _load_dashscope_creds()
        if not creds:
            return None
            
        api_key = creds.get("api_key")
        expires_at_str = creds.get("expires_at")
        
        if not api_key or not expires_at_str:
            return None
            
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            # Check if token is still valid (with 5 minute buffer)
            if expires_at > (datetime.now() + timedelta(minutes=5)):
                return api_key
        except ValueError:
            # Invalid date format, invalidate cache
            pass
            
        # Remove expired cache
        try:
            DASHSCOPE_CACHE_FILE.unlink()
        except Exception:
            pass
            
        return None
    
    @staticmethod
    def clear_cache() -> None:
        """Clear the DashScope API key cache."""
        try:
            if DASHSCOPE_CACHE_FILE.exists():
                DASHSCOPE_CACHE_FILE.unlink()
        except Exception:
            pass