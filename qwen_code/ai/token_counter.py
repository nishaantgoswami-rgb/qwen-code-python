"""
Advanced token counting utilities for AI models with accurate tracking.
"""

import logging
from typing import List, Union, Any
from dataclasses import dataclass


@dataclass
class TokenUsage:
    """Enhanced token usage information with more detailed tracking."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_read_tokens: int = 0  # Tokens read from cache
    cache_write_tokens: int = 0  # Tokens written to cache
    reasoning_tokens: int = 0  # Reasoning tokens (for models that support this)

    @property
    def effective_tokens(self) -> int:
        """Total tokens that count against quota (excluding cache tokens)."""
        return self.total_tokens + self.reasoning_tokens

    def add(self, other: 'TokenUsage') -> 'TokenUsage':
        """Add another TokenUsage to this one."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens
        )

    def __add__(self, other: 'TokenUsage') -> 'TokenUsage':
        return self.add(other)


class AdvancedTokenCounter:
    """
    Advanced token counter with model-specific tokenization and accurate tracking.
    """
    
    def __init__(self, model_name: str = "qwen3-coder-plus"):
        self.model_name = model_name
        self._encoders = {}
        
    def _get_encoder(self, model_name: str):
        """Get appropriate encoder for the model."""
        if model_name not in self._encoders:
            try:
                import tiktoken
                # Try to get encoder specific to the model
                if "qwen" in model_name.lower():
                    # For Qwen models, use a compatible tokenizer
                    self._encoders[model_name] = tiktoken.get_encoding("cl100k_base")
                elif "gpt-4" in model_name or "gpt-3.5" in model_name:
                    self._encoders[model_name] = tiktoken.encoding_for_model(model_name.replace("gpt-3.5", "gpt-3.5-turbo"))
                else:
                    # Default to cl100k_base for other models
                    self._encoders[model_name] = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                # tiktoken is not available, set to None to use fallback
                self._encoders[model_name] = None
                logging.warning(f"tiktoken not available, using fallback token counting for {model_name}")
            except Exception:
                # Fallback to cl100k_base
                try:
                    import tiktoken
                    self._encoders[model_name] = tiktoken.get_encoding("cl100k_base")
                except:
                    self._encoders[model_name] = None
                    logging.warning(f"Could not get encoder for {model_name}, using fallback")
        return self._encoders[model_name]
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using appropriate encoder."""
        encoder = self._get_encoder(self.model_name)
        if encoder:
            try:
                import tiktoken
                return len(encoder.encode(text))
            except Exception:
                # Fallback to simple estimation if encoding fails
                return max(1, len(text) // 4)
        else:
            # Fallback to simple estimation
            return max(1, len(text) // 4)
    
    def count_message_tokens(self, message: Any) -> int:
        """Count tokens in a message with accurate accounting."""
        # For Qwen and similar models, we need to account for role and content
        # Format: {role}: {content}
        formatted_text = f"{message.role}: {message.content}"
        return self.count_tokens(formatted_text)
    
    def count_message_list_tokens(self, messages: List[Any]) -> int:
        """Count total tokens in a list of messages."""
        total = 0
        for msg in messages:
            # Update token count in message object if not already set
            if hasattr(msg, 'token_count') and msg.token_count == 0:
                msg.token_count = self.count_message_tokens(msg)
            elif not hasattr(msg, 'token_count'):
                # If no token_count attribute, just calculate and return
                total += self.count_message_tokens(msg)
            else:
                total += msg.token_count
        return total
    
    def estimate_response_tokens(self, prompt: str) -> int:
        """Estimate the number of tokens in the likely response."""
        # This is a heuristic - typically responses are shorter than prompts
        # but for coding tasks, responses might be longer
        prompt_tokens = self.count_tokens(prompt)
        # For coding tasks, assume response might be 1.2x the prompt size
        return int(prompt_tokens * 1.2)
    
    def get_available_context_tokens(self, max_context: int, messages: List[Any], 
                                   estimated_response_tokens: int = None) -> int:
        """Calculate available tokens for new messages."""
        current_tokens = self.count_message_list_tokens(messages)
        estimated_response = estimated_response_tokens or self.estimate_response_tokens(
            messages[-1].content if messages else ""
        )
        return max_context - current_tokens - estimated_response


class ContextWindowManager:
    """
    Manages context window and message truncation with intelligent preservation.
    """
    
    def __init__(self, max_context_tokens: int = 32000, token_safety_margin: int = 1000):
        self.max_context_tokens = max_context_tokens
        self.token_safety_margin = token_safety_margin
        self.effective_max_tokens = max_context_tokens - token_safety_margin
        
    def calculate_context_tokens(self, messages: List[Any], token_counter: AdvancedTokenCounter) -> int:
        """Calculate total context tokens from messages using accurate token counter."""
        return token_counter.count_message_list_tokens(messages)
    
    def truncate_messages(self, messages: List[Any], token_counter: AdvancedTokenCounter, 
                         max_tokens: int = None) -> List[Any]:
        """
        Truncate messages to fit within context window while preserving important context.
        
        Args:
            messages: List of messages to truncate
            token_counter: Token counter to use for calculations
            max_tokens: Maximum tokens allowed (defaults to effective_max_tokens)
            
        Returns:
            Truncated list of messages that fit within the token limit
        """
        if not messages:
            return messages
            
        target_tokens = max_tokens or self.effective_max_tokens
        
        # First, ensure all messages have their token counts calculated
        total_tokens = self.calculate_context_tokens(messages, token_counter)
        
        if total_tokens <= target_tokens:
            return messages
        
        # Start with a strategy to preserve important context
        preserved_messages = []
        current_tokens = 0
        
        # Always preserve system message if it exists (usually at index 0)
        if messages and hasattr(messages[0], 'role') and messages[0].role == "system":
            system_msg = messages[0]
            if hasattr(system_msg, 'token_count') and system_msg.token_count == 0:
                system_msg.token_count = token_counter.count_message_tokens(system_msg)
            elif not hasattr(system_msg, 'token_count'):
                system_msg.token_count = token_counter.count_message_tokens(system_msg)
                
            msg_tokens = getattr(system_msg, 'token_count', token_counter.count_message_tokens(system_msg))
            if msg_tokens <= target_tokens:
                preserved_messages.append(system_msg)
                current_tokens += msg_tokens
            else:
                # System message exceeds token limit - this is an edge case
                logging.warning(f"System message exceeds context limit: {msg_tokens} > {target_tokens}")
                # For now, just include the truncated system message
                preserved_messages.append(self._truncate_message_for_tokens(
                    system_msg, token_counter, target_tokens
                ))
                current_tokens = target_tokens
                return preserved_messages
        
        # Calculate how many tokens we have left after preserving system message
        remaining_tokens = target_tokens - current_tokens
        
        # Preserve recent messages (user and assistant pairs)
        recent_messages = []
        recent_tokens = 0
        
        # Go backwards through messages to preserve recent exchanges
        for i in range(len(messages) - 1, -1, -1):
            if (hasattr(messages[i], 'role') and messages[i].role == "system" and i == 0):  # Skip system message as it's already preserved
                continue
                
            msg = messages[i]
            if hasattr(msg, 'token_count'):
                msg_tokens = msg.token_count if msg.token_count > 0 else token_counter.count_message_tokens(msg)
            else:
                msg_tokens = token_counter.count_message_tokens(msg)
            
            if recent_tokens + msg_tokens <= remaining_tokens:
                recent_messages.append((i, msg))
                recent_tokens += msg_tokens
            else:
                break
        
        # Reverse to get them back in chronological order
        recent_messages.reverse()
        
        # Add preserved and recent messages
        preserved_messages.extend([msg for _, msg in recent_messages])
        current_tokens += recent_tokens
        
        # If we still have space and there are important earlier messages, include them
        remaining_tokens = target_tokens - current_tokens
        if remaining_tokens > 0:
            # Look for important messages from the beginning (excluding system and already included recent messages)
            important_indices = {i for i, _ in recent_messages}
            
            for i in range(1, len(messages)):  # Start from 1 to skip system message
                if i in important_indices or recent_tokens >= len(messages) - len(recent_messages):
                    continue
                
                msg = messages[i]
                if hasattr(msg, 'token_count'):
                    msg_tokens = msg.token_count if msg.token_count > 0 else token_counter.count_message_tokens(msg)
                else:
                    msg_tokens = token_counter.count_message_tokens(msg)
                
                # Check if message is important (contains code, is long, or is a substantial user query)
                is_important = self._is_message_important(msg)
                
                if is_important and current_tokens + msg_tokens <= target_tokens:
                    preserved_messages.append(msg)
                    current_tokens += msg_tokens
                    important_indices.add(i)
                    
                    if current_tokens >= target_tokens:
                        break
        
        return preserved_messages
    
    def _is_message_important(self, message: Any) -> bool:
        """Determine if a message is important to preserve."""
        # Check if message has content attribute
        if not hasattr(message, 'content'):
            return False
        if not hasattr(message, 'role'):
            return False
            
        # Contains code blocks
        if '```' in message.content:
            return True
        # Is a long message (>200 words)
        if len(message.content.split()) > 200:
            return True
        # Is a substantial user query (>20 words)
        if message.role == "user" and len(message.content.split()) > 20:
            return True
        # Contains certain key terms that suggest importance
        key_terms = ["error", "bug", "fix", "solution", "important", "critical", "implement", "create"]
        if any(term in message.content.lower() for term in key_terms):
            return True
        return False
    
    def _truncate_message_for_tokens(self, message: Any, token_counter: AdvancedTokenCounter, 
                                   target_tokens: int) -> Any:
        """Truncate a single message to fit within token limit."""
        if token_counter.count_message_tokens(message) <= target_tokens:
            return message
        
        # Simple truncation by reducing content
        content_tokens = token_counter.count_tokens(message.content)
        if content_tokens <= target_tokens:
            return message
        
        # Estimate how much content we can keep
        content_per_token = len(message.content) / content_tokens
        max_content_length = int(target_tokens * content_per_token * 0.8)  # Use 80% to be safe
        
        truncated_content = message.content[:max_content_length]
        
        # Create a new message with truncated content
        # If the original has timestamp attribute, preserve it, otherwise use current time
        timestamp = getattr(message, 'timestamp', datetime.now())
        
        # Import the Message class here to avoid circular import
        from .client import Message
        truncated_message = Message(
            role=message.role,
            content=truncated_content,
            timestamp=timestamp
        )
        truncated_message.token_count = token_counter.count_message_tokens(truncated_message)
        
        return truncated_message