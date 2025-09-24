"""
Authentication providers for Qwen Code following the API specification.
"""

import asyncio
import aiohttp
import webbrowser
import json
import base64
import hashlib
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from contextlib import contextmanager
import httpx


@dataclass
class AuthResult:
    """Authentication result container."""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class Credentials:
    """Authentication credentials container."""
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    client_id: Optional[str] = None


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""
    
    def __init__(self):
        self._credentials: Optional[Credentials] = None
    
    @abstractmethod
    async def authenticate(self) -> AuthResult:
        """Perform authentication process."""
        pass
    
    @abstractmethod
    async def refresh_token(self) -> AuthResult:
        """Refresh authentication token."""
        pass
    
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if current authentication is valid."""
        pass
    
    def get_credentials(self) -> Optional[Credentials]:
        """Get current credentials."""
        return self._credentials


class PKCEHelper:
    """Helper class for PKCE (Proof Key for Code Exchange) implementation."""
    
    @staticmethod
    def generate_code_verifier() -> str:
        """Generate a code verifier for PKCE."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    @staticmethod
    def generate_code_challenge(code_verifier: str) -> str:
        """Generate a code challenge from a code verifier."""
        sha256_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(sha256_hash).decode('utf-8').rstrip('=')


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""
    
    def do_GET(self):
        """Handle GET requests (OAuth callback)."""
        # Parse the query parameters
        query_params = parse_qs(self.path.split('?', 1)[1] if '?' in self.path else '')
        
        # Extract authorization code
        auth_code = query_params.get('code', [None])[0]
        error = query_params.get('error', [None])[0]
        
        # Store the result in the server
        self.server.auth_code = auth_code
        self.server.error = error
        
        # Send response to browser
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        if auth_code:
            response_html = """
            <html>
            <head><title>Authentication Successful</title></head>
            <body>
                <h1>Authentication Successful!</h1>
                <p>You can close this window and return to the application.</p>
            </body>
            </html>
            """
        else:
            response_html = """
            <html>
            <head><title>Authentication Failed</title></head>
            <body>
                <h1>Authentication Failed!</h1>
                <p>Please try again or check the application for more details.</p>
            </body>
            </html>
            """
        
        self.wfile.write(response_html.encode('utf-8'))
        
        # Signal that we're done
        self.server.running = False


class OAuthCallbackServer:
    """Local server to handle OAuth callback."""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.httpd = None
        self.auth_code = None
        self.error = None
    
    def start(self):
        """Start the server."""
        self.httpd = HTTPServer(('localhost', self.port), OAuthCallbackHandler)
        self.httpd.auth_code = None
        self.httpd.error = None
        self.httpd.running = True
        
        # Start server in a separate thread
        server_thread = Thread(target=self._serve)
        server_thread.daemon = True
        server_thread.start()
        return server_thread
    
    def _serve(self):
        """Run the server."""
        try:
            while self.httpd.running:
                self.httpd.handle_request()
        except Exception:
            pass  # Server was stopped
    
    def stop(self):
        """Stop the server."""
        if self.httpd:
            self.httpd.running = False


class QwenOAuthProvider(AuthProvider):
    """Qwen OAuth 2.0 authentication provider with PKCE."""
    
    def __init__(self, client_id: str, redirect_uri: str, client_secret: Optional[str] = None):
        super().__init__()
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.client_secret = client_secret
        self.auth_base_url = "https://chat.qwen.ai"
        # Use the correct OAuth2 endpoints as per API specification
        self.api_base_url = f"{self.auth_base_url}/api/v1/oauth2"
        self.token_url = f"{self.api_base_url}/token"
        self.authorize_url = f"{self.auth_base_url}/oauth2/authorize"
        self.device_code_url = f"{self.api_base_url}/device/code"
        
    def has_valid_cached_credentials(self) -> bool:
        """Check if we have valid cached credentials."""
        from qwen_code.auth.credentials import CredentialManager
        cred_manager = CredentialManager()
        
        # First check the encrypted database
        credentials = cred_manager.load_credentials("qwen_oauth")
        if credentials and credentials.access_token:
            # Check if token is still valid
            if credentials.expires_at:
                from datetime import datetime, timedelta
                try:
                    expires_at = datetime.fromisoformat(credentials.expires_at)
                    # If token is still valid (with 5 minute buffer), return True
                    return expires_at > (datetime.now() + timedelta(minutes=5))
                except ValueError:
                    return False
            return True
        
        # Fallback to JSON file
        cached_tokens = cred_manager.load_tokens_from_json()
        
        if not cached_tokens or not cached_tokens.get('access_token'):
            return False
        
        # Check if token is still valid
        expires_at_str = cached_tokens.get('expires_at')
        if expires_at_str:
            from datetime import datetime, timedelta
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                # If token is still valid (with 5 minute buffer), return True
                return expires_at > (datetime.now() + timedelta(minutes=5))
            except ValueError:
                return False
        
        return True
    
    async def authenticate(self, use_device_flow: bool = False) -> AuthResult:
        """Initiate OAuth flow with browser authentication or device code flow."""
        # Try loading cached credentials first
        from qwen_code.auth.credentials import CredentialManager
        cred_manager = CredentialManager()
        
        # First check the encrypted database
        credentials = cred_manager.load_credentials("qwen_oauth")
        if credentials and credentials.access_token:
            # Check if token is still valid
            if credentials.expires_at:
                from datetime import datetime, timedelta
                try:
                    expires_at = datetime.fromisoformat(credentials.expires_at)
                    # If token is still valid (with 5 minute buffer), use it
                    if expires_at > (datetime.now() + timedelta(minutes=5)):
                        access_token = credentials.access_token
                        refresh_token = credentials.refresh_token
                        
                        # Store in credentials
                        self._credentials = Credentials(
                            provider="qwen_oauth",
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_at=expires_at,
                            client_id=self.client_id
                        )
                        
                        return AuthResult(
                            success=True,
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_at=expires_at
                        )
                except ValueError:
                    pass  # Invalid date format, continue with authentication
        
        # Fallback to JSON file
        cached_tokens = cred_manager.load_tokens_from_json()
        
        if cached_tokens and cached_tokens.get('access_token'):
            # Check if token is still valid
            expires_at_str = cached_tokens.get('expires_at')
            if expires_at_str:
                from datetime import datetime, timedelta
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    # If token is still valid (with 5 minute buffer), use it
                    if expires_at > (datetime.now() + timedelta(minutes=5)):
                        access_token = cached_tokens['access_token']
                        refresh_token = cached_tokens.get('refresh_token')
                        
                        # Store in credentials
                        self._credentials = Credentials(
                            provider="qwen_oauth",
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_at=expires_at,
                            client_id=self.client_id
                        )
                        
                        return AuthResult(
                            success=True,
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_at=expires_at
                        )
                except ValueError:
                    pass  # Invalid date format, continue with authentication
        
        # If no valid cached credentials, proceed with authentication
        if use_device_flow:
            return await self._authenticate_device_flow()
        else:
            return await self._authenticate_web_flow()
    
    async def _authenticate_web_flow(self) -> AuthResult:
        """Initiate OAuth flow with browser authentication."""
        try:
            # Generate PKCE parameters
            code_verifier = PKCEHelper.generate_code_verifier()
            code_challenge = PKCEHelper.generate_code_challenge(code_verifier)
            
            # Start local callback server
            callback_server = OAuthCallbackServer()
            server_thread = callback_server.start()
            
            # Construct authorization URL
            auth_params = {
                'response_type': 'code',
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'scope': 'openid profile email model.completion',
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            
            auth_url = f"{self.authorize_url}?{urlencode(auth_params)}"
            
            # Open browser for user authentication
            webbrowser.open(auth_url)
            
            # Wait for callback (with timeout)
            timeout = 120  # 2 minutes
            start_time = time.time()
            
            while callback_server.httpd.running and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1)
            
            # Stop the server
            callback_server.stop()
            
            # Check if we got an authorization code
            if not callback_server.httpd.auth_code:
                error_msg = callback_server.httpd.error or "Authentication timeout or cancelled"
                return AuthResult(
                    success=False,
                    error_message=f"OAuth authentication failed: {error_msg}"
                )
            
            # Exchange authorization code for tokens
            token_result = await self._exchange_code_for_tokens(
                callback_server.httpd.auth_code,
                code_verifier
            )
            
            if not token_result.success:
                return token_result
            
            # Store credentials
            self._credentials = Credentials(
                provider="qwen_oauth",
                access_token=token_result.access_token,
                refresh_token=token_result.refresh_token,
                expires_at=token_result.expires_at,
                client_id=self.client_id
            )
            
            # Save tokens to JSON file for compatibility
            token_data = {
                'access_token': token_result.access_token,
                'refresh_token': token_result.refresh_token,
                'expires_at': token_result.expires_at.isoformat() if token_result.expires_at else None,
                'client_id': self.client_id
            }
            
            # Save tokens using credential manager
            cred_manager = CredentialManager()
            cred_manager.save_tokens_to_json(token_data)
            
            # Clear DashScope API key cache when OAuth tokens change
            from qwen_code.auth.dashscope_exchange import DashScopeTokenExchange
            DashScopeTokenExchange.clear_cache()
            
            return token_result
            
        except Exception as e:
            return AuthResult(
                success=False,
                error_message=f"OAuth authentication failed: {str(e)}"
            )
    
    async def refresh_token(self) -> AuthResult:
        """Refresh authentication token."""
        # Load credentials if not already loaded
        if not self._credentials:
            from qwen_code.auth.credentials import CredentialManager
            cred_manager = CredentialManager()
            
            # Try to load from encrypted database first
            credentials = cred_manager.load_credentials("qwen_oauth")
            if not credentials:
                # Fallback to JSON file
                cached_tokens = cred_manager.load_tokens_from_json()
                if cached_tokens and cached_tokens.get('access_token'):
                    from datetime import datetime
                    expires_at_str = cached_tokens.get('expires_at')
                    expires_at = None
                    if expires_at_str:
                        try:
                            expires_at = datetime.fromisoformat(expires_at_str)
                        except ValueError:
                            pass
                    
                    credentials = Credentials(
                        provider="qwen_oauth",
                        access_token=cached_tokens['access_token'],
                        refresh_token=cached_tokens.get('refresh_token'),
                        expires_at=expires_at
                    )
            
            self._credentials = credentials
        
        if not self._credentials or not self._credentials.refresh_token:
            return AuthResult(
                success=False,
                error_message="No refresh token available"
            )
        
        try:
            # Prepare token refresh request
            token_data = {
                'grant_type': 'refresh_token',
                'refresh_token': self._credentials.refresh_token,
                'client_id': self._credentials.client_id if hasattr(self._credentials, 'client_id') else self.client_id
            }
            
            # Add client secret if provided
            if self.client_secret:
                token_data['client_secret'] = self.client_secret

            # Make token refresh request with proper headers
            token_url = self.token_url
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Qwen-Code-CLI/1.0"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=token_data, headers=headers, allow_redirects=False)
                if response.status != 200:
                    error_text = response.text
                    # Try to decode the error response as JSON to get more details
                    try:
                        error_response = response.json()
                        error_msg = error_response.get('error', {}).get('message', error_text)
                    except json.JSONDecodeError:
                        error_msg = error_text
                    
                    return AuthResult(
                        success=False,
                        error_message=f"Token refresh failed with status {response.status}: {error_msg}"
                    )
                
                token_response = response.json()
                
                # Update credentials
                access_token = token_response.get('access_token')
                refresh_token = token_response.get('refresh_token', self._credentials.refresh_token)
                expires_in = token_response.get('expires_in', 3600)
                
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Update stored credentials
                self._credentials.access_token = access_token
                self._credentials.refresh_token = refresh_token
                self._credentials.expires_at = expires_at
                
                # Save updated credentials
                from qwen_code.auth.credentials import CredentialManager
                cred_manager = CredentialManager()
                cred_manager.store_credentials(self._credentials)
                
                # Also save to JSON file for compatibility
                token_data = {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'expires_at': expires_at.isoformat() if expires_at else None,
                    'client_id': self.client_id
                }
                cred_manager.save_tokens_to_json(token_data)
                
                # Clear DashScope API key cache when OAuth tokens change
                from qwen_code.auth.dashscope_exchange import DashScopeTokenExchange
                DashScopeTokenExchange.clear_cache()
                
                return AuthResult(
                    success=True,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at
                )
                
        except Exception as e:
            return AuthResult(
                success=False,
                error_message=f"Token refresh failed: {str(e)}"
            )
    
    async def get_device_code(self) -> dict:
        """Get device code for device flow authentication."""
        try:
            # Generate PKCE parameters
            code_verifier = PKCEHelper.generate_code_verifier()
            code_challenge = PKCEHelper.generate_code_challenge(code_verifier)
            
            # Prepare device code request with PKCE
            device_data = {
                'client_id': self.client_id,
                'scope': 'openid profile email model.completion',
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            
            # Make device code request with proper headers
            device_url = self.device_code_url
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Qwen-Code-CLI/1.0"
            }
            
            # Add debugging information
            print(f"DEBUG: Requesting device code from {device_url}")
            print(f"DEBUG: Client ID: {self.client_id}")
            print(f"DEBUG: Headers: {headers}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(device_url, data=device_data, headers=headers, allow_redirects=False)
                if response.status != 200:
                    error_text = response.text
                    print(f"DEBUG: Device code request failed with status {response.status}")
                    print(f"DEBUG: Response text: {error_text}")
                    raise Exception(f"Device code request failed with status {response.status}: {error_text}")
                
                device_response = response.json()
                print(f"DEBUG: Device code response received successfully")
                
                # Store code_verifier for later use in token exchange
                device_response['code_verifier'] = code_verifier
                return device_response
                
        except Exception as e:
            print(f"DEBUG: Device code request failed with error: {str(e)}")
            raise Exception(f"Device code request failed: {str(e)}")
    
    async def poll_for_token(self, device_code: str, code_verifier: str, interval: int = 5, expires_in: int = 600) -> AuthResult:
        """Poll for token using device code."""
        try:
            start_time = time.time()
            timeout = expires_in  # Use the expires_in value from device code response
            
            async with httpx.AsyncClient() as client:
                while (time.time() - start_time) < timeout:
                    # Prepare token request - for device code flow, we should not include redirect_uri
                    token_data = {
                        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                        'device_code': device_code,
                        'client_id': self.client_id,
                        'code_verifier': code_verifier
                    }
                    
                    # Add client secret if provided (some OAuth implementations require it for device flow)
                    if self.client_secret:
                        token_data['client_secret'] = self.client_secret
                    
                    # Make token request
                    token_url = self.token_url
                    
                    headers = {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "Qwen-Code-CLI/1.0"
                    }
                    
                    response = await client.post(token_url, data=token_data, headers=headers, allow_redirects=False)
                    if response.status == 200:
                        token_response = response.json()
                        
                        access_token = token_response.get('access_token')
                        refresh_token = token_response.get('refresh_token')
                        expires_in = token_response.get('expires_in', 3600)
                        
                        expires_at = datetime.now() + timedelta(seconds=expires_in)
                        
                        # Store credentials
                        self._credentials = Credentials(
                            provider="qwen_oauth",
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_at=expires_at,
                            client_id=self.client_id
                        )
                        
                        return AuthResult(
                            success=True,
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_at=expires_at
                        )
                    elif response.status == 400:
                        try:
                            error_response = response.json()
                        except json.JSONDecodeError:
                            # If response is not JSON, use the raw text
                            return AuthResult(
                                success=False,
                                error_message=f"Device code authentication failed with status {response.status}: {response.text}"
                            )
                        
                        error = error_response.get('error')
                        
                        # According to OAuth2 spec, device flow has specific error codes
                        if error == 'authorization_pending':
                            # User has not authorized yet, continue polling
                            await asyncio.sleep(interval)
                            continue
                        elif error == 'slow_down':
                            # Server is asking us to slow down, increase the interval
                            interval = min(interval * 1.5, 10)
                            await asyncio.sleep(interval)
                            continue
                        elif error == 'expired_token':
                            # Device code has expired, return error
                            error_description = error_response.get('error_description', 'Device code has expired')
                            return AuthResult(
                                success=False,
                                error_message=f"Device code expired: {error_description}"
                            )
                        elif error == 'access_denied':
                            # User denied the authorization
                            error_description = error_response.get('error_description', 'User denied authorization')
                            return AuthResult(
                                success=False,
                                error_message=f"Access denied: {error_description}"
                            )
                        elif error == 'invalid_grant':
                            # Device code is invalid
                            error_description = error_response.get('error_description', 'Invalid device code')
                            return AuthResult(
                                success=False,
                                error_message=f"Invalid grant: {error_description}"
                            )
                        else:
                            # Other error, stop polling
                            error_description = error_response.get('error_description', 'Unknown error')
                            return AuthResult(
                                success=False,
                                error_message=f"Device code authentication failed: {error} - {error_description}"
                            )
                    else:
                        error_text = response.text
                        return AuthResult(
                            success=False,
                            error_message=f"Device code authentication failed with status {response.status}: {error_text}"
                        )
            
            # Timeout reached
            return AuthResult(
                success=False,
                error_message="Device code authentication timed out"
            )
                
        except Exception as e:
            return AuthResult(
                success=False,
                error_message=f"Device code authentication failed: {str(e)}"
            )
    
    async def _authenticate_device_flow(self) -> AuthResult:
        """Initiate OAuth flow with device code."""
        try:
            # Get device code
            device_response = await self.get_device_code()
            
            device_code = device_response.get('device_code')
            user_code = device_response.get('user_code')
            verification_uri_complete = device_response.get('verification_uri_complete')
            interval = device_response.get('interval', 5)
            expires_in = device_response.get('expires_in', 600)
            code_verifier = device_response.get('code_verifier')
            
            # Display instructions to user
            print(f"Device code authentication:")
            if verification_uri_complete:
                auth_url = verification_uri_complete
                print(f"1. Go to: {auth_url}")
            else:
                verification_uri = device_response.get('verification_uri')
                auth_url = verification_uri
                print(f"1. Go to: {auth_url}")
                print(f"2. Enter code: {user_code}")
            print(f"3. Wait for authentication to complete...")
            
            # Attempt to open the browser automatically
            try:
                import webbrowser
                webbrowser.open(auth_url)
            except Exception as e:
                print(f"Could not automatically open browser: {e}")
                print("Please manually open the URL in your browser.")
            
            # Poll for token
            result = await self.poll_for_token(device_code, code_verifier, interval, expires_in)
            
            # If successful, save tokens to JSON file
            if result.success:
                # Create token data to save
                token_data = {
                    'access_token': result.access_token,
                    'refresh_token': result.refresh_token,
                    'expires_at': result.expires_at.isoformat() if result.expires_at else None
                }
                
                # Save tokens using credential manager
                cred_manager = CredentialManager()
                cred_manager.save_tokens_to_json(token_data)
            
            return result
            
        except Exception as e:
            return AuthResult(
                success=False,
                error_message=f"Device code authentication failed: {str(e)}"
            )
    
    async def _exchange_code_for_tokens(self, auth_code: str, code_verifier: str) -> AuthResult:
        """Exchange authorization code for access and refresh tokens."""
        try:
            # Prepare token request
            token_data = {
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': self.redirect_uri,
                'client_id': self.client_id,
                'code_verifier': code_verifier
            }
            
            # Add client secret if provided
            if self.client_secret:
                token_data['client_secret'] = self.client_secret
            
            # Make token exchange request with proper headers
            token_url = self.token_url
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Qwen-Code-CLI/1.0"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=token_data, headers=headers, allow_redirects=False)
                if response.status != 200:
                    error_text = response.text
                    # Try to decode the error response as JSON to get more details
                    try:
                        error_response = response.json()
                        error_msg = error_response.get('error', {}).get('message', error_text)
                    except json.JSONDecodeError:
                        error_msg = error_text
                    
                    return AuthResult(
                        success=False,
                        error_message=f"Token exchange failed with status {response.status}: {error_msg}"
                    )
                
                token_response = response.json()
                
                access_token = token_response.get('access_token')
                refresh_token = token_response.get('refresh_token')
                expires_in = token_response.get('expires_in', 3600)
                
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                return AuthResult(
                    success=True,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at
                )
                
        except Exception as e:
            return AuthResult(
                success=False,
                error_message=f"Token exchange failed: {str(e)}"
            )
    
    def is_valid(self) -> bool:
        """Check if current authentication is valid."""
        # First check if we have credentials in memory
        if self._credentials and self._credentials.access_token:
            if not self._credentials.expires_at:
                return True
            # Consider token expired 5 minutes before actual expiration to allow for refresh
            from datetime import datetime, timedelta
            return self._credentials.expires_at > (datetime.now() + timedelta(minutes=5))
        
        # If no credentials in memory, check stored credentials
        from qwen_code.auth.credentials import CredentialManager
        cred_manager = CredentialManager()
        
        # Check encrypted database first
        credentials = cred_manager.load_credentials("qwen_oauth")
        if credentials and credentials.access_token:
            if not credentials.expires_at:
                # Store in memory for next check
                self._credentials = credentials
                return True
            try:
                from datetime import datetime, timedelta
                expires_at = datetime.fromisoformat(credentials.expires_at)
                # Consider token expired 5 minutes before actual expiration to allow for refresh
                is_valid = expires_at > (datetime.now() + timedelta(minutes=5))
                if is_valid:
                    # Store in memory for next check
                    self._credentials = credentials
                return is_valid
            except ValueError:
                return False
        
        # Fallback to JSON file
        json_creds = cred_manager.load_tokens_from_json()
        if json_creds and json_creds.get('access_token'):
            expires_at_str = json_creds.get('expires_at')
            if not expires_at_str:
                return True
            try:
                from datetime import datetime, timedelta
                expires_at = datetime.fromisoformat(expires_at_str)
                # Consider token expired 5 minutes before actual expiration to allow for refresh
                return expires_at > (datetime.now() + timedelta(minutes=5))
            except ValueError:
                return False
        
        return False


class OpenAICompatibleProvider(AuthProvider):
    """OpenAI-compatible API key authentication provider."""
    
    def __init__(self, api_key: str, base_url: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
    
    async def authenticate(self) -> AuthResult:
        """Authenticate using API key."""
        # For API key auth, we just store the key as the access token
        self._credentials = Credentials(
            provider="openai_compatible",
            access_token=self.api_key
        )
        return AuthResult(success=True, access_token=self.api_key)
    
    async def refresh_token(self) -> AuthResult:
        """Refresh authentication token."""
        # For API key auth, no refresh is needed
        if self._credentials:
            return AuthResult(success=True, access_token=self._credentials.access_token)
        return AuthResult(
            success=False,
            error_message="No credentials available"
        )
    
    def is_valid(self) -> bool:
        """Check if current authentication is valid."""
        return self._credentials is not None and bool(self._credentials.access_token)


class RegionalAuthProvider(AuthProvider):
    """Base class for regional authentication providers like ModelScope, Alibaba Cloud, OpenRouter."""
    
    def __init__(self, provider_name: str, api_key: str, base_url: str):
        super().__init__()
        self.provider_name = provider_name
        self.api_key = api_key
        self.base_url = base_url
    
    async def authenticate(self) -> AuthResult:
        """Authenticate using API key."""
        self._credentials = Credentials(
            provider=self.provider_name,
            access_token=self.api_key
        )
        return AuthResult(success=True, access_token=self.api_key)
    
    async def refresh_token(self) -> AuthResult:
        """Refresh authentication token."""
        # For API key auth, no refresh is needed
        if self._credentials:
            return AuthResult(success=True, access_token=self._credentials.access_token)
        return AuthResult(
            success=False,
            error_message="No credentials available"
        )
    
    def is_valid(self) -> bool:
        """Check if current authentication is valid."""
        return self._credentials is not None and bool(self._credentials.access_token)


class ModelScopeProvider(RegionalAuthProvider):
    """ModelScope API authentication provider."""
    
    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/api/v1"):
        super().__init__("modelscope", api_key, base_url)


class AlibabaCloudProvider(RegionalAuthProvider):
    """Alibaba Cloud API authentication provider."""
    
    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/api/v1"):
        super().__init__("alibaba_cloud", api_key, base_url)


class OpenRouterProvider(RegionalAuthProvider):
    """OpenRouter API authentication provider."""
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        super().__init__("openrouter", api_key, base_url)