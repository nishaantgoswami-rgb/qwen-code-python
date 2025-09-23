"""
DashScope token exchange mechanism for converting Qwen OAuth tokens to DashScope API keys.

This module handles the process of exchanging OAuth tokens obtained from Qwen's OAuth flow
for DashScope API keys that can be used with the DashScope compatible API endpoint.

The exchange process:
1. Takes a Qwen OAuth token
2. Sends it to a DashScope token exchange endpoint
3. Receives a DashScope API key in response
4. Caches the API key for future use

Note: The exact endpoint for token exchange is still to be confirmed and may need to be updated.
"""

import json
import time
import httpx
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

# DashScope token exchange endpoint (placeholder - needs to be confirmed)
DASHSCOPE_TOKEN_EXCHANGE_URL = "https://dashscope.aliyuncs.com/api/v1/tokens/from-qwen-oauth"

# Cache file for DashScope API keys
DASHSCOPE_CACHE_FILE = Path.home() / ".qwen" / "dashscope_api_keys.json"


def _save_dashscope_creds(creds: Dict[str, Any]) -> None:
    """Save DashScope credentials to JSON file."""
    DASHSCOPE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DASHSCOPE_CACHE_FILE.write_text(json.dumps(creds))


def _load_dashscope_creds() -> Optional[Dict[str, Any]]:
    """Load DashScope credentials from JSON file."""
    if DASHSCOPE_CACHE_FILE.exists():
        try:
            return json.loads(DASHSCOPE_CACHE_FILE.read_text())
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
            
        # Try multiple possible endpoints
        possible_endpoints = [
            "https://dashscope.aliyuncs.com/api/v1/tokens/from-qwen-oauth",
            "https://dashscope.aliyuncs.com/api/v1/user/apikeys/exchange",
            "https://chat.qwen.ai/api/v1/dashscope/key",
            "https://dashscope.aliyuncs.com/api/v1/apikeys"
        ]
        
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        for endpoint in possible_endpoints:
            try:
                async with httpx.AsyncClient() as client:
                    # Try POST first
                    response = await client.post(
                        endpoint,
                        headers=headers,
                        json={}
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
                    
                    # If POST fails, try GET
                    if response.status_code in [404, 405]:
                        response = await client.get(
                            endpoint,
                            headers=headers
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
                                
            except Exception as e:
                # Continue to next endpoint
                continue
                
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
            
        # Try multiple possible endpoints
        possible_endpoints = [
            "https://dashscope.aliyuncs.com/api/v1/tokens/from-qwen-oauth",
            "https://dashscope.aliyuncs.com/api/v1/user/apikeys/exchange",
            "https://chat.qwen.ai/api/v1/dashscope/key",
            "https://dashscope.aliyuncs.com/api/v1/apikeys"
        ]
        
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        for endpoint in possible_endpoints:
            try:
                with httpx.Client() as client:
                    # Try POST first
                    response = client.post(
                        endpoint,
                        headers=headers,
                        json={}
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
                    
                    # If POST fails, try GET
                    if response.status_code in [404, 405]:
                        response = client.get(
                            endpoint,
                            headers=headers
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
                                
            except Exception as e:
                # Continue to next endpoint
                continue
                
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