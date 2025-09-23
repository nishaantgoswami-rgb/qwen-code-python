"""
Clean version of the Qwen AI client with proper resource_url handling
"""

import aiohttp
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, AsyncIterator, Literal
from datetime import datetime


@dataclass
class TokenUsage:
    """Token usage information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class Message:
    """Chat message container."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AIResponse:
    """AI model response container."""
    content: str
    usage: TokenUsage
    model: str
    timestamp: datetime = field(default_factory=datetime.now)


class AIClient(ABC):
    """Abstract base class for AI model clients."""
    
    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs) -> AIResponse:
        """Send chat messages to AI model."""
        pass
    
    @abstractmethod
    async def stream_chat(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream chat response from AI model."""
        pass


class QwenClient(AIClient):
    """Qwen AI model client implementation with OAuth2 support."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen3-coder-plus", is_oauth_token: bool = False):
        """
        Initialize QwenClient.
        
        Args:
            api_key: API key or OAuth2 token. If None, will use OAuth2 flow.
            model: Model name to use.
            is_oauth_token: Whether the provided api_key is an OAuth2 token.
        """
        self.api_key = api_key
        self.model = model
        self.is_oauth_token = is_oauth_token
        # Use DashScope compatible mode endpoint as default
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # Import here to avoid circular imports
        if not api_key and not is_oauth_token:
            from qwen_code.auth.enhanced_oauth2_client import QwenOAuth2Client
            self.oauth_client = QwenOAuth2Client()
        else:
            self.oauth_client = None
    
    def _get_api_key(self) -> str:
        """Get a valid API key or OAuth2 token."""
        if self.oauth_client:
            # Use OAuth token directly instead of trying to exchange it through get_dashscope_api_key
            return self.oauth_client.get_access_token()
        elif self.api_key:
            return self.api_key
        else:
            raise ValueError("No API key or OAuth2 client available")
    
    def _is_using_oauth_token(self) -> bool:
        """Check if we're currently using an OAuth token (not exchanged for API key)."""
        if self.oauth_client:
            # When using OAuth client, we're always using an OAuth token
            return True
        return self.is_oauth_token
    
    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        api_key = self._get_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # For Qwen OAuth tokens, we need to indicate the auth type to DashScope
        if self._is_using_oauth_token():
            headers["X-DashScope-AuthType"] = "QWEN_OAUTH"
        
        # Enable cache control for Qwen/DashScope providers by default
        headers["X-DashScope-CacheControl"] = "enable"
        
        # Add UserAgent header as required by DashScope API
        headers["X-DashScope-UserAgent"] = "qwen-code-py/2.0.0"
        
        return headers
    
    def _get_base_url(self) -> str:
        """Get the base URL for API requests."""
        # For OAuth tokens, use the resource_url from OAuth response as per TypeScript implementation
        if self.oauth_client and hasattr(self.oauth_client, '_creds'):
            resource_url = self.oauth_client._creds.get("resource_url")
            if resource_url:
                # Ensure it has the proper protocol
                if not resource_url.startswith("http"):
                    resource_url = f"https://{resource_url}"
                # Remove trailing slash if present
                resource_url = resource_url.rstrip("/")
                # The resource_url may come in different forms:
                # - https://portal.qwen.ai -> should become https://portal.qwen.ai/v1 for API
                # - https://portal.qwen.ai/api/v1 -> already correct for API
                if not resource_url.endswith("/v1"):
                    # If it doesn't end with /v1, we need to determine the correct path
                    if resource_url.endswith("/api"):
                        # Example: https://portal.qwen.ai/api -> https://portal.qwen.ai/api/v1
                        resource_url = f"{resource_url}/v1"
                    elif resource_url.endswith("/api/v1"):
                        # Already correct format
                        pass
                    else:
                        # Example: https://portal.qwen.ai -> https://portal.qwen.ai/v1
                        # Based on your debug, this was the working format
                        resource_url = f"{resource_url}/v1"
                return resource_url
        # Fallback to DashScope compatible mode endpoint
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    async def chat(self, messages: List[Message], **kwargs) -> AIResponse:
        """Send chat request to Qwen API."""
        try:
            # Convert messages to the format expected by the API
            api_messages = [
                {
                    "role": msg.role,
                    "content": msg.content
                }
                for msg in messages
            ]
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "stream": False
            }
            
            # Add any additional parameters from kwargs
            payload.update(kwargs)
            
            headers = self._get_headers()
            base_url = self._get_base_url()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Qwen API request failed with status {response.status}: {error_text}")
                    
                    response_data = await response.json()
                    
                    # Extract content and usage information
                    content = response_data["choices"][0]["message"]["content"]
                    usage_data = response_data.get("usage", {})
                    
                    usage = TokenUsage(
                        prompt_tokens=usage_data.get("prompt_tokens", 0),
                        completion_tokens=usage_data.get("completion_tokens", 0),
                        total_tokens=usage_data.get("total_tokens", 0)
                    )
                    
                    return AIResponse(
                        content=content,
                        usage=usage,
                        model=response_data.get("model", self.model),
                        timestamp=datetime.now()
                    )
                    
        except Exception as e:
            # Fallback to simulated response in case of error
            return AIResponse(
                content=f"Error connecting to Qwen API: {str(e)}",
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                model=self.model
            )
    
    async def stream_chat(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream chat response from Qwen API."""
        try:
            # Convert messages to the format expected by the API
            api_messages = [
                {
                    "role": msg.role,
                    "content": msg.content
                }
                for msg in messages
            ]
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "stream": True
            }
            
            # Add any additional parameters from kwargs
            payload.update(kwargs)
            
            headers = self._get_headers()
            base_url = self._get_base_url()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"Error connecting to Qwen API: {response.status} - {error_text}"
                        return
                    
                    # Process the streaming response
                    async for line in response.content:
                        if line:
                            line_str = line.decode()
                            if line_str.startswith('data: '):
                                data = line_str[6:]  # Remove 'data: ' prefix
                                if data.strip() == '[DONE]':
                                    break
                                try:
                                    json_data = json.loads(data)
                                    if 'choices' in json_data and len(json_data['choices']) > 0:
                                        delta = json_data['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    # Skip invalid JSON lines
                                    pass
                                    
        except Exception as e:
            yield f"Error connecting to Qwen API: {str(e)}"


class OpenAICompatibleClient(AIClient):
    """OpenAI-compatible AI model client."""
    
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.model = model
    
    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat(self, messages: List[Message], **kwargs) -> AIResponse:
        """Send chat request to OpenAI-compatible API."""
        try:
            # Convert messages to the format expected by the API
            api_messages = [
                {
                    "role": msg.role,
                    "content": msg.content
                }
                for msg in messages
            ]
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "stream": False
            }
            
            # Add any additional parameters from kwargs
            payload.update(kwargs)
            
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI-compatible API request failed with status {response.status}: {error_text}")
                    
                    response_data = await response.json()
                    
                    # Extract content and usage information
                    content = response_data["choices"][0]["message"]["content"]
                    usage_data = response_data.get("usage", {})
                    
                    usage = TokenUsage(
                        prompt_tokens=usage_data.get("prompt_tokens", 0),
                        completion_tokens=usage_data.get("completion_tokens", 0),
                        total_tokens=usage_data.get("total_tokens", 0)
                    )
                    
                    return AIResponse(
                        content=content,
                        usage=usage,
                        model=response_data.get("model", self.model),
                        timestamp=datetime.now()
                    )
                    
        except Exception as e:
            # Fallback to simulated response in case of error
            return AIResponse(
                content=f"Error connecting to OpenAI-compatible API: {str(e)}",
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                model=self.model
            )
    
    async def stream_chat(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream chat response from OpenAI-compatible API."""
        try:
            # Convert messages to the format expected by the API
            api_messages = [
                {
                    "role": msg.role,
                    "content": msg.content
                }
                for msg in messages
            ]
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "stream": True
            }
            
            # Add any additional parameters from kwargs
            payload.update(kwargs)
            
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"Error connecting to OpenAI-compatible API: {response.status} - {error_text}"
                        return
                    
                    # Process the streaming response
                    async for line in response.content:
                        if line:
                            line_str = line.decode()
                            if line_str.startswith('data: '):
                                data = line_str[6:]  # Remove 'data: ' prefix
                                if data.strip() == '[DONE]':
                                    break
                                try:
                                    json_data = json.loads(data)
                                    if 'choices' in json_data and len(json_data['choices']) > 0:
                                        delta = json_data['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    # Skip invalid JSON lines
                                    pass
                                    
        except Exception as e:
            yield f"Error connecting to OpenAI-compatible API: {str(e)}"