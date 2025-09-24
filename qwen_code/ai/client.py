"""
Enhanced Qwen AI client with complete token counting, context management, 
model-specific parsing, error recovery, and rate limiting.
"""

import aiohttp
import json
import asyncio
import time
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, AsyncIterator, Literal, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
from .parser import QwenParser
from .token_counter import AdvancedTokenCounter, ContextWindowManager, TokenUsage


# TokenUsage is now imported from token_counter, so we can remove this definition
# @dataclass
# class TokenUsage:
#     """Token usage information."""
#     prompt_tokens: int = 0
#     completion_tokens: int = 0
#     total_tokens: int = 0


@dataclass
class Message:
    """Chat message container."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0  # Token count for this message


@dataclass
class AIResponse:
    """AI model response container."""
    content: str
    usage: TokenUsage
    model: str
    timestamp: datetime = field(default_factory=datetime.now)
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class RateLimit:
    """Rate limiting information."""
    requests_per_minute: int
    tokens_per_minute: int
    remaining_requests: int
    remaining_tokens: int
    reset_time: datetime


class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: int, error_code: str = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.response_data = response_data


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


# Token counter functionality is now in token_counter.py, so we can remove this class
# class TokenCounter:
#     """Token counting utility for different models."""
#     
#     def __init__(self, model_name: str = "qwen3-coder-plus"):
#         self.model_name = model_name
#         self._tokenizer = None
#         
#     def _get_tokenizer(self):
#         """Get appropriate tokenizer for the model."""
#         if self._tokenizer is None:
#             try:
#                 import tiktoken
#                 # Use gpt-4 tokenizer as a proxy for Qwen models since they're similar
#                 self._tokenizer = tiktoken.get_encoding("cl100k_base")
#             except ImportError:
#                 # Fallback to simple word counting
#                 logging.warning("tiktoken not available, using fallback token counting")
#                 self._tokenizer = None
#         return self._tokenizer
#     
#     def count_tokens(self, text: str) -> int:
#         """Count tokens in text using appropriate method."""
#         if self._tokenizer:
#             try:
#                 import tiktoken
#                 # Use a reasonable fallback tokenizer
#                 enc = self._tokenizer
#                 return len(enc.encode(text))
#             except Exception:
#                 # Fallback to simple estimation
#                 return len(text.split())
#         else:
#             # Simple estimation: ~4 chars per token
#             return max(1, len(text) // 4)
#     
#     def count_message_tokens(self, message: Message) -> int:
#         """Count tokens in a message."""
#         return self.count_tokens(f"{message.role}: {message.content}")


class QwenClient(AIClient):
    """Enhanced Qwen AI model client implementation with complete token counting, 
    context management, error recovery, and rate limiting."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen3-coder-plus", 
                 is_oauth_token: bool = False, max_retries: int = 3, 
                 retry_delay: float = 1.0, request_timeout: int = 120,
                 max_context_tokens: int = 32000, token_safety_margin: int = 1000):
        """
        Initialize QwenClient with enhanced features.
        
        Args:
            api_key: API key or OAuth2 token. If None, will use OAuth2 flow.
            model: Model name to use.
            is_oauth_token: Whether the provided api_key is an OAuth2 token.
            max_retries: Maximum number of retry attempts.
            retry_delay: Base delay between retries (exponential backoff).
            request_timeout: Request timeout in seconds.
            max_context_tokens: Maximum context tokens allowed by the model.
            token_safety_margin: Safety margin to reserve for API overhead.
        """
        self.api_key = api_key
        self.model = model
        self.is_oauth_token = is_oauth_token
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.request_timeout = request_timeout
        self.advanced_token_counter = AdvancedTokenCounter(model)
        self.context_manager = ContextWindowManager(max_context_tokens, token_safety_margin)
        self.parser = QwenParser()
        
        # Rate limiting tracking
        self.rate_limits: Dict[str, RateLimit] = {}
        self._last_request_times: List[float] = []
        self._max_requests_per_minute = 100  # Conservative default
        
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
        
        # Add Client header to identify the application
        headers["X-DashScope-Client"] = "qwen-code-python"
        
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
        # Fallback to DashScope compatible mode endpoint for OAuth tokens
        if self._is_using_oauth_token():
            return "https://dashscope.aliyuncs.com/compatible-mode/v1"
        # Otherwise, default to DashScope compatible mode endpoint
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = time.time()
        # Remove requests older than 60 seconds
        self._last_request_times = [t for t in self._last_request_times if now - t < 60]
        
        # Check if we're under the rate limit
        if len(self._last_request_times) >= self._max_requests_per_minute:
            return False
        
        # Record this request time
        self._last_request_times.append(now)
        return True
    
    async def _wait_for_rate_limit(self):
        """Wait until we're within rate limits."""
        while not self._check_rate_limit():
            await asyncio.sleep(1)
    
    async def _make_request(self, url: str, headers: dict, payload: dict, 
                           session: aiohttp.ClientSession) -> dict:
        """Make an API request with error handling and rate limiting."""
        # Wait for rate limit before making request
        await self._wait_for_rate_limit()
        
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        async with session.post(url, headers=headers, json=payload, timeout=timeout) as response:
            # Extract rate limit headers if present
            self._update_rate_limits(response.headers)
            
            response_status = response.status
            if response_status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                
                # Handle different error statuses
                if response_status == 429:
                    # Rate limit exceeded
                    raise APIError(f"Rate limit exceeded: {error_text}", response_status, "rate_limit_exceeded")
                elif response_status >= 500:
                    # Server error - likely temporary, should retry
                    raise APIError(f"Server error: {response_status} - {error_text}", response_status, "server_error")
                else:
                    # Other error - don't retry
                    raise APIError(f"API request failed: {response_status} - {error_text}", response_status, "request_failed")
    
    def _update_rate_limits(self, headers: dict):
        """Update rate limit information from response headers."""
        # DashScope rate limit headers
        if 'X-RateLimit-Limit-Requests' in headers:
            try:
                limit_requests = int(headers.get('X-RateLimit-Limit-Requests', ''))
                remaining_requests = int(headers.get('X-RateLimit-Remaining-Requests', ''))
                reset_time_str = headers.get('X-RateLimit-Reset-Requests')
                
                if reset_time_str:
                    reset_time = datetime.fromtimestamp(int(reset_time_str))
                else:
                    reset_time = datetime.now() + timedelta(minutes=1)
                
                self.rate_limits['requests'] = RateLimit(
                    requests_per_minute=limit_requests,
                    tokens_per_minute=0,  # Not provided in headers
                    remaining_requests=remaining_requests,
                    remaining_tokens=0,  # Not provided in headers
                    reset_time=reset_time
                )
            except (ValueError, TypeError):
                pass  # Ignore if headers are malformed
        
        if 'X-RateLimit-Limit-Tokens' in headers:
            try:
                limit_tokens = int(headers.get('X-RateLimit-Limit-Tokens', ''))
                remaining_tokens = int(headers.get('X-RateLimit-Remaining-Tokens', ''))
                reset_time_str = headers.get('X-RateLimit-Reset-Tokens')
                
                if reset_time_str:
                    reset_time = datetime.fromtimestamp(int(reset_time_str))
                else:
                    reset_time = datetime.now() + timedelta(minutes=1)
                
                self.rate_limits['tokens'] = RateLimit(
                    requests_per_minute=0,  # Not provided in headers
                    tokens_per_minute=limit_tokens,
                    remaining_requests=0,  # Not provided in headers
                    remaining_tokens=remaining_tokens,
                    reset_time=reset_time
                )
            except (ValueError, TypeError):
                pass  # Ignore if headers are malformed
    
    def _calculate_context_tokens(self, messages: List[Message]) -> int:
        """Calculate total context tokens from messages using advanced token counter."""
        return self.advanced_token_counter.count_message_list_tokens(messages)
    
    def _truncate_messages_for_context(self, messages: List[Message], 
                                      max_context_tokens: int = None) -> List[Message]:
        """Truncate messages to fit within context window using advanced context manager."""
        if not messages:
            return messages
        
        # Use provided max_context_tokens or default to the context manager's setting
        target_tokens = max_context_tokens or self.context_manager.effective_max_tokens
        
        # Use the advanced context manager to truncate messages intelligently
        return self.context_manager.truncate_messages(messages, self.advanced_token_counter, target_tokens)
    
    async def _retry_request(self, url: str, headers: dict, payload: dict, 
                            is_streaming: bool = False) -> tuple:
        """Make a request with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    if is_streaming:
                        # For streaming, we need to handle retries differently
                        # Return session and response so caller can handle streaming
                        await self._wait_for_rate_limit()
                        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
                        response = await session.post(url, headers=headers, json=payload, timeout=timeout)
                        self._update_rate_limits(response.headers)
                        
                        if response.status == 200:
                            return session, response
                        else:
                            if response.status == 429:
                                error_text = await response.text()
                                raise APIError(f"Rate limit exceeded: {error_text}", response.status, "rate_limit_exceeded")
                            else:
                                error_text = await response.text()
                                if response.status >= 500:
                                    raise APIError(f"Server error: {response.status} - {error_text}", response.status, "server_error")
                                else:
                                    raise APIError(f"API request failed: {response.status} - {error_text}", response.status, "request_failed")
                    else:
                        # For non-streaming requests
                        result = await self._make_request(url, headers, payload, session)
                        return result, None
            
            except APIError as e:
                last_exception = e
                if e.error_code in ["rate_limit_exceeded", "server_error"]:
                    # These errors are retryable
                    if attempt < self.max_retries:
                        # Exponential backoff
                        wait_time = self.retry_delay * (2 ** attempt)
                        logging.warning(f"API error (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}. Retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise e
                else:
                    # Other errors are not retryable
                    raise e
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    # Exponential backoff for other exceptions too
                    wait_time = self.retry_delay * (2 ** attempt)
                    logging.warning(f"Network error (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}. Retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise e
        
        # If we get here, all retries failed
        raise last_exception or Exception("Request failed after all retries")
    
    async def chat(self, messages: List[Message], **kwargs) -> AIResponse:
        """Send chat request to Qwen API with enhanced token counting and error handling."""
        try:
            # Validate and truncate messages for context window
            max_context_tokens = kwargs.get('max_context_tokens', 30000)
            processed_messages = self._truncate_messages_for_context(messages, max_context_tokens)
            
            # Calculate input tokens before making the request
            input_tokens = self.advanced_token_counter.count_message_list_tokens(processed_messages)
            
            # Convert messages to the format expected by the API
            api_messages = []
            for msg in processed_messages:
                # Ensure token count is calculated for all messages
                if msg.token_count == 0:
                    msg.token_count = self.advanced_token_counter.count_message_tokens(msg)
                
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "stream": False
            }
            
            # Add any additional parameters from kwargs
            payload.update(kwargs)
            
            headers = self._get_headers()
            base_url = self._get_base_url()
            url = f"{base_url}/chat/completions"
            
            # Make request with retry logic
            response_data, _ = await self._retry_request(url, headers, payload, is_streaming=False)
            
            # Extract content and usage information
            content = response_data["choices"][0]["message"]["content"]
            usage_data = response_data.get("usage", {})
            
            # Create enhanced token usage object
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                cache_read_tokens=usage_data.get("cache_read_tokens", 0),
                cache_write_tokens=usage_data.get("cache_write_tokens", 0),
                reasoning_tokens=usage_data.get(" reasoning_tokens", 0)
            )
            
            # Log token usage for debugging
            logging.info(f"QwenClient.chat - Input tokens: {input_tokens}, "
                        f"Output tokens: {usage.completion_tokens}, "
                        f"Total tokens: {usage.total_tokens}")
            
            return AIResponse(
                content=content,
                usage=usage,
                model=response_data.get("model", self.model),
                timestamp=datetime.now(),
                raw_response=response_data
            )
            
        except APIError as e:
            logging.error(f"API Error in QwenClient.chat: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in QwenClient.chat: {str(e)}")
            # Fallback to simulated response in case of error
            return AIResponse(
                content=f"Error connecting to Qwen API: {str(e)}",
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                model=self.model
            )
    
    async def stream_chat(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream chat response from Qwen API with enhanced error handling."""
        try:
            # Validate and truncate messages for context window
            max_context_tokens = kwargs.get('max_context_tokens', 30000)
            processed_messages = self._truncate_messages_for_context(messages, max_context_tokens)
            
            # Calculate input tokens before making the request
            input_tokens = self.advanced_token_counter.count_message_list_tokens(processed_messages)
            
            # Convert messages to the format expected by the API
            api_messages = []
            for msg in processed_messages:
                # Ensure token count is calculated for all messages
                if msg.token_count == 0:
                    msg.token_count = self.advanced_token_counter.count_message_tokens(msg)
                
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "stream": True
            }
            
            # Add any additional parameters from kwargs
            payload.update(kwargs)
            
            headers = self._get_headers()
            base_url = self._get_base_url()
            url = f"{base_url}/chat/completions"
            
            # Make request with retry logic for streaming
            session, response = await self._retry_request(url, headers, payload, is_streaming=True)
            
            if response.status != 200:
                error_text = await response.text()
                yield f"Error connecting to Qwen API: {response.status} - {error_text}"
                return
            
            try:
                # Process the streaming response and collect tokens
                full_content = ""
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
                                        full_content += content
                                        yield content
                            except json.JSONDecodeError:
                                # Skip invalid JSON lines
                                pass
            finally:
                # Clean up resources
                await response.release()
                await session.close()
                
                # Calculate and log token usage for streaming response
                output_tokens = self.advanced_token_counter.count_tokens(full_content)
                logging.info(f"QwenClient.stream_chat - Input tokens: {input_tokens}, "
                            f"Output tokens: {output_tokens}, "
                            f"Total streamed: {len(full_content)} characters")
                
        except APIError as e:
            logging.error(f"API Error in QwenClient.stream_chat: {e}")
            yield f"Error connecting to Qwen API: {str(e)}"
        except Exception as e:
            logging.error(f"Unexpected error in QwenClient.stream_chat: {str(e)}")
            yield f"Error connecting to Qwen API: {str(e)}"

    def get_context_summary(self, messages: List[Message]) -> dict:
        """Get summary of context usage for debugging."""
        total_tokens = self._calculate_context_tokens(messages)
        message_count = len(messages)
        
        # Breakdown by role
        role_breakdown = {}
        for msg in messages:
            role = msg.role
            tokens = msg.token_count or self.advanced_token_counter.count_message_tokens(msg)
            if role not in role_breakdown:
                role_breakdown[role] = {"count": 0, "tokens": 0}
            role_breakdown[role]["count"] += 1
            role_breakdown[role]["tokens"] += tokens
        
        # Calculate remaining context
        remaining_tokens = self.context_manager.effective_max_tokens - total_tokens
        
        return {
            "total_messages": message_count,
            "total_tokens": total_tokens,
            "remaining_tokens": max(0, remaining_tokens),
            "max_context_tokens": self.context_manager.max_context_tokens,
            "effective_max_tokens": self.context_manager.effective_max_tokens,
            "average_tokens_per_message": total_tokens / message_count if message_count > 0 else 0,
            "role_breakdown": role_breakdown,
            "model": self.model,
            "compression_needed": total_tokens > self.context_manager.effective_max_tokens
        }


class OpenAICompatibleClient(AIClient):
    """OpenAI-compatible AI model client with enhanced features."""
    
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4",
                 max_retries: int = 3, retry_delay: float = 1.0, 
                 request_timeout: int = 120,
                 max_context_tokens: int = 128000, token_safety_margin: int = 1000):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.request_timeout = request_timeout
        self.advanced_token_counter = AdvancedTokenCounter(model)
        self.context_manager = ContextWindowManager(max_context_tokens, token_safety_margin)
        self.parser = QwenParser()
        
        # Rate limiting tracking
        self.rate_limits: Dict[str, RateLimit] = {}
        self._last_request_times: List[float] = []
        self._max_requests_per_minute = 100  # Conservative default
    
    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = time.time()
        # Remove requests older than 60 seconds
        self._last_request_times = [t for t in self._last_request_times if now - t < 60]
        
        # Check if we're under the rate limit
        if len(self._last_request_times) >= self._max_requests_per_minute:
            return False
        
        # Record this request time
        self._last_request_times.append(now)
        return True
    
    async def _wait_for_rate_limit(self):
        """Wait until we're within rate limits."""
        while not self._check_rate_limit():
            await asyncio.sleep(1)
    
    async def _make_request(self, url: str, headers: dict, payload: dict, 
                           session: aiohttp.ClientSession) -> dict:
        """Make an API request with error handling and rate limiting."""
        # Wait for rate limit before making request
        await self._wait_for_rate_limit()
        
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        async with session.post(url, headers=headers, json=payload, timeout=timeout) as response:
            response_status = response.status
            if response_status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                
                # Handle different error statuses
                if response_status == 429:
                    # Rate limit exceeded
                    raise APIError(f"Rate limit exceeded: {error_text}", response_status, "rate_limit_exceeded")
                elif response_status >= 500:
                    # Server error - likely temporary, should retry
                    raise APIError(f"Server error: {response_status} - {error_text}", response_status, "server_error")
                else:
                    # Other error - don't retry
                    raise APIError(f"API request failed: {response_status} - {error_text}", response_status, "request_failed")
    
    def _calculate_context_tokens(self, messages: List[Message]) -> int:
        """Calculate total context tokens from messages using advanced token counter."""
        return self.advanced_token_counter.count_message_list_tokens(messages)
    
    def _truncate_messages_for_context(self, messages: List[Message], 
                                      max_context_tokens: int = None) -> List[Message]:
        """Truncate messages to fit within context window using advanced context manager."""
        if not messages:
            return messages
        
        # Use provided max_context_tokens or default to the context manager's setting
        target_tokens = max_context_tokens or self.context_manager.effective_max_tokens
        
        # Use the advanced context manager to truncate messages intelligently
        return self.context_manager.truncate_messages(messages, self.advanced_token_counter, target_tokens)
    
    async def _retry_request(self, url: str, headers: dict, payload: dict, 
                            is_streaming: bool = False) -> tuple:
        """Make a request with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    if is_streaming:
                        # For streaming, we need to handle retries differently
                        # Return session and response so caller can handle streaming
                        await self._wait_for_rate_limit()
                        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
                        response = await session.post(url, headers=headers, json=payload, timeout=timeout)
                        
                        if response.status == 200:
                            return session, response
                        else:
                            error_text = await response.text()
                            if response.status == 429:
                                raise APIError(f"Rate limit exceeded: {error_text}", response.status, "rate_limit_exceeded")
                            elif response.status >= 500:
                                raise APIError(f"Server error: {response.status} - {error_text}", response.status, "server_error")
                            else:
                                raise APIError(f"API request failed: {response.status} - {error_text}", response.status, "request_failed")
                    else:
                        # For non-streaming requests
                        result = await self._make_request(url, headers, payload, session)
                        return result, None
            
            except APIError as e:
                last_exception = e
                if e.error_code in ["rate_limit_exceeded", "server_error"]:
                    # These errors are retryable
                    if attempt < self.max_retries:
                        # Exponential backoff
                        wait_time = self.retry_delay * (2 ** attempt)
                        logging.warning(f"API error (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}. Retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise e
                else:
                    # Other errors are not retryable
                    raise e
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    # Exponential backoff for other exceptions too
                    wait_time = self.retry_delay * (2 ** attempt)
                    logging.warning(f"Network error (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}. Retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise e
        
        # If we get here, all retries failed
        raise last_exception or Exception("Request failed after all retries")
    
    async def chat(self, messages: List[Message], **kwargs) -> AIResponse:
        """Send chat request to OpenAI-compatible API."""
        try:
            # Validate and truncate messages for context window
            max_context_tokens = kwargs.get('max_context_tokens', 30000)
            processed_messages = self._truncate_messages_for_context(messages, max_context_tokens)
            
            # Calculate input tokens before making the request
            input_tokens = self.advanced_token_counter.count_message_list_tokens(processed_messages)
            
            # Convert messages to the format expected by the API
            api_messages = []
            for msg in processed_messages:
                # Ensure token count is calculated for all messages
                if msg.token_count == 0:
                    msg.token_count = self.advanced_token_counter.count_message_tokens(msg)
                
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "stream": False
            }
            
            # Add any additional parameters from kwargs
            payload.update(kwargs)
            
            headers = self._get_headers()
            
            # Make request with retry logic
            response_data, _ = await self._retry_request(f"{self.base_url}/chat/completions", headers, payload, is_streaming=False)
            
            # Extract content and usage information
            content = response_data["choices"][0]["message"]["content"]
            usage_data = response_data.get("usage", {})
            
            # Create enhanced token usage object
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                cache_read_tokens=usage_data.get("cache_read_tokens", 0),
                cache_write_tokens=usage_data.get("cache_write_tokens", 0),
                reasoning_tokens=usage_data.get(" reasoning_tokens", 0)
            )
            
            # Log token usage for debugging
            logging.info(f"OpenAICompatibleClient.chat - Input tokens: {input_tokens}, "
                        f"Output tokens: {usage.completion_tokens}, "
                        f"Total tokens: {usage.total_tokens}")
            
            return AIResponse(
                content=content,
                usage=usage,
                model=response_data.get("model", self.model),
                timestamp=datetime.now(),
                raw_response=response_data
            )
            
        except APIError as e:
            logging.error(f"API Error in OpenAICompatibleClient.chat: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in OpenAICompatibleClient.chat: {str(e)}")
            # Fallback to simulated response in case of error
            return AIResponse(
                content=f"Error connecting to OpenAI-compatible API: {str(e)}",
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                model=self.model
            )
    
    async def stream_chat(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream chat response from OpenAI-compatible API."""
        try:
            # Validate and truncate messages for context window
            max_context_tokens = kwargs.get('max_context_tokens', 30000)
            processed_messages = self._truncate_messages_for_context(messages, max_context_tokens)
            
            # Calculate input tokens before making the request
            input_tokens = self.advanced_token_counter.count_message_list_tokens(processed_messages)
            
            # Convert messages to the format expected by the API
            api_messages = []
            for msg in processed_messages:
                # Ensure token count is calculated for all messages
                if msg.token_count == 0:
                    msg.token_count = self.advanced_token_counter.count_message_tokens(msg)
                
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "stream": True
            }
            
            # Add any additional parameters from kwargs
            payload.update(kwargs)
            
            headers = self._get_headers()
            
            # Make request with retry logic for streaming
            session, response = await self._retry_request(f"{self.base_url}/chat/completions", headers, payload, is_streaming=True)
            
            if response.status != 200:
                error_text = await response.text()
                yield f"Error connecting to OpenAI-compatible API: {response.status} - {error_text}"
                return
            
            try:
                # Process the streaming response and collect tokens
                full_content = ""
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
                                        full_content += content
                                        yield content
                            except json.JSONDecodeError:
                                # Skip invalid JSON lines
                                pass
            finally:
                # Clean up resources
                await response.release()
                await session.close()
                
                # Calculate and log token usage for streaming response
                output_tokens = self.advanced_token_counter.count_tokens(full_content)
                logging.info(f"OpenAICompatibleClient.stream_chat - Input tokens: {input_tokens}, "
                            f"Output tokens: {output_tokens}, "
                            f"Total streamed: {len(full_content)} characters")
                
        except APIError as e:
            logging.error(f"API Error in OpenAICompatibleClient.stream_chat: {e}")
            yield f"Error connecting to OpenAI-compatible API: {str(e)}"
        except Exception as e:
            logging.error(f"Unexpected error in OpenAICompatibleClient.stream_chat: {str(e)}")
            yield f"Error connecting to OpenAI-compatible API: {str(e)}"