"""
Unit tests for Qwen Code AI clients.
"""

import pytest
import asyncio
from qwen_code.ai.client import QwenClient, OpenAICompatibleClient, Message, TokenUsage


class TestQwenClient:
    """Test Qwen AI client."""
    
    def test_init(self):
        """Test client initialization."""
        client = QwenClient("test-key", "test-model")
        assert client.api_key == "test-key"
        assert client.model == "test-model"
        assert client.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    @pytest.mark.asyncio
    async def test_chat(self):
        """Test chat method."""
        client = QwenClient("test-key", "test-model")
        
        # Test the chat method
        messages = [Message(role="user", content="Hello")]
        response = await client.chat(messages)
        
        # Verify the response
        assert "simulated response from Qwen" in response.content
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30
        assert response.model == "test-model"
    
    @pytest.mark.asyncio
    async def test_stream_chat(self):
        """Test stream chat method."""
        client = QwenClient("test-key", "test-model")
        
        # Test the stream chat method
        messages = [Message(role="user", content="Hello")]
        chunks = []
        async for chunk in client.stream_chat(messages):
            chunks.append(chunk)
        
        # Verify the chunks
        assert len(chunks) > 0
        assert "simulated streaming response from Qwen" in "".join(chunks)


class TestOpenAICompatibleClient:
    """Test OpenAI-compatible client."""
    
    def test_init(self):
        """Test client initialization."""
        client = OpenAICompatibleClient("test-key", "https://api.openai.com/v1", "test-model")
        assert client.api_key == "test-key"
        assert client.base_url == "https://api.openai.com/v1"
        assert client.model == "test-model"
    
    @pytest.mark.asyncio
    async def test_chat(self):
        """Test chat method."""
        client = OpenAICompatibleClient("test-key", "https://api.openai.com/v1", "test-model")
        
        # Test the chat method
        messages = [Message(role="user", content="Hello")]
        response = await client.chat(messages)
        
        # Verify the response
        assert "simulated response from an OpenAI-compatible API" in response.content
        assert response.usage.prompt_tokens == 15
        assert response.usage.completion_tokens == 25
        assert response.usage.total_tokens == 40
        assert response.model == "test-model"
    
    @pytest.mark.asyncio
    async def test_stream_chat(self):
        """Test stream chat method."""
        client = OpenAICompatibleClient("test-key", "https://api.openai.com/v1", "test-model")
        
        # Test the stream chat method
        messages = [Message(role="user", content="Hello")]
        chunks = []
        async for chunk in client.stream_chat(messages):
            chunks.append(chunk)
        
        # Verify the chunks
        assert len(chunks) > 0
        assert "simulated streaming response from an OpenAI-compatible API" in "".join(chunks)