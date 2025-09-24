"""
API rate limiting implementation for Qwen Code.
Implements comprehensive rate limiting for API calls to prevent abuse.
"""

import time
import threading
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
from qwen_code.utils.logging import get_logger


logger = get_logger()


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    per: str       # Identifier for rate limiting (e.g., 'user', 'ip', 'api_key')


class RateLimiter:
    """
    API rate limiter with sliding window algorithm.
    """
    
    def __init__(self):
        self._limits: Dict[str, RateLimitConfig] = {}
        self._request_times: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self._lock = threading.Lock()

    def add_limit(self, name: str, config: RateLimitConfig) -> None:
        """
        Add a rate limit configuration.
        
        Args:
            name: Name of the rate limit (e.g., 'chat_api', 'auth_api')
            config: RateLimitConfig object
        """
        self._limits[name] = config
        # logger.info(f"Rate limit added: {name} - {config.requests} requests per {config.window} seconds")  # Removed for cleaner UI

    def is_allowed(self, name: str, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if a request is allowed based on rate limits.
        
        Args:
            name: Name of the rate limit to check
            identifier: Unique identifier (e.g., user ID, IP address, API key)
            
        Returns:
            Tuple of (is_allowed, reset_time_in_seconds)
        """
        if name not in self._limits:
            logger.warning(f"Rate limit configuration '{name}' not found")
            return True, None

        config = self._limits[name]
        
        with self._lock:
            # Get request times for this identifier
            request_times = self._request_times[name][identifier]
            current_time = time.time()
            
            # Remove requests that are outside the time window
            while request_times and current_time - request_times[0] > config.window:
                request_times.popleft()
            
            # Check if we're under the limit
            if len(request_times) < config.requests:
                # Add current request time
                request_times.append(current_time)
                return True, int(request_times[0] + config.window) if request_times else None
            else:
                # Rate limit exceeded
                reset_time = int(request_times[0] + config.window)
                logger.warning(f"Rate limit exceeded for {identifier} on {name}. Reset in {reset_time - int(current_time)} seconds")
                return False, reset_time

    def get_remaining_requests(self, name: str, identifier: str) -> Tuple[int, int]:
        """
        Get remaining requests and reset time.
        
        Args:
            name: Name of the rate limit
            identifier: Unique identifier
            
        Returns:
            Tuple of (remaining_requests, reset_time_in_seconds)
        """
        if name not in self._limits:
            return 0, 0

        config = self._limits[name]
        
        with self._lock:
            request_times = self._request_times[name][identifier]
            current_time = time.time()
            
            # Remove requests that are outside the time window
            while request_times and current_time - request_times[0] > config.window:
                request_times.popleft()
            
            remaining = max(0, config.requests - len(request_times))
            reset_time = int(request_times[0] + config.window) if request_times else int(current_time + config.window)
            
            return remaining, reset_time


class APIRateLimiter:
    """
    Enhanced API rate limiter with multiple rate limit policies.
    """
    
    def __init__(self):
        self._rate_limiter = RateLimiter()
        self._setup_default_limits()
    
    def _setup_default_limits(self) -> None:
        """Setup default rate limits for different API endpoints."""
        # Chat API limits
        self._rate_limiter.add_limit("chat_api", RateLimitConfig(
            requests=60,  # 60 requests per minute
            window=60,
            per="user"
        ))
        
        # Auth API limits (more restrictive)
        self._rate_limiter.add_limit("auth_api", RateLimitConfig(
            requests=10,  # 10 requests per minute
            window=60,
            per="ip"
        ))
        
        # File operations (lower limit)
        self._rate_limiter.add_limit("file_operations", RateLimitConfig(
            requests=100,  # 100 operations per minute
            window=60,
            per="user"
        ))
        
        # Token refresh (very restrictive)
        self._rate_limiter.add_limit("token_refresh", RateLimitConfig(
            requests=5,  # 5 refresh attempts per minute
            window=60,
            per="user"
        ))
        
        # logger.info("Default rate limits configured")  # Removed for cleaner UI

    def check_rate_limit(self, endpoint: str, identifier: str) -> Tuple[bool, Dict[str, int]]:
        """
        Check if a request to an endpoint is allowed based on rate limits.
        
        Args:
            endpoint: The API endpoint name (e.g., 'chat_api', 'auth_api')
            identifier: Unique identifier for the requester
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        is_allowed, reset_time = self._rate_limiter.is_allowed(endpoint, identifier)
        
        remaining, reset_time = self._rate_limiter.get_remaining_requests(endpoint, identifier)
        
        rate_limit_info = {
            "remaining": remaining,
            "reset_time": reset_time
        }
        
        if not is_allowed:
            # Only log rate limit exceeded to file, not to console (avoids cluttering UI)
            # logger.warning(f"Rate limit exceeded for {identifier} on {endpoint}")
            # Log the attempt for security monitoring
            # logger.info(f"Rate limit attempt logged: {identifier} on {endpoint}")
            pass  # Placeholder to satisfy Python syntax requirement
        
        return is_allowed, rate_limit_info

    def add_custom_limit(self, name: str, requests: int, window: int, per: str) -> None:
        """
        Add a custom rate limit.
        
        Args:
            name: Name of the rate limit
            requests: Number of requests allowed
            window: Time window in seconds
            per: Identifier type
        """
        config = RateLimitConfig(requests=requests, window=window, per=per)
        self._rate_limiter.add_limit(name, config)

    def get_rate_limit_headers(self, endpoint: str, identifier: str) -> Dict[str, str]:
        """
        Get rate limit headers for API responses.
        
        Args:
            endpoint: The API endpoint name
            identifier: Unique identifier for the requester
            
        Returns:
            Dictionary with rate limit headers
        """
        remaining, reset_time = self._rate_limiter.get_remaining_requests(endpoint, identifier)
        
        # Get the config to get the total limit
        if endpoint in self._rate_limiter._limits:
            total_limit = self._rate_limiter._limits[endpoint].requests
        else:
            total_limit = 0
            
        headers = {
            "X-RateLimit-Limit": str(total_limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time)
        }
        
        return headers


# Global rate limiter instance
api_rate_limiter = APIRateLimiter()