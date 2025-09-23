#!/usr/bin/env python3
"""
Test script for Qwen OAuth2 client and AI integration.
"""

from qwen_code.auth import QwenOAuth2Client
from qwen_code.ai import QwenClient, Message


def test_oauth_client():
    """Test the OAuth2 client."""
    print("Testing Qwen OAuth2 client...")
    client = QwenOAuth2Client()
    try:
        token = client.get_access_token()
        print(f"Successfully obtained access token: {token[:20]}...")
        return True
    except Exception as e:
        print(f"Failed to obtain access token: {e}")
        return False


def test_qwen_client():
    """Test the Qwen AI client."""
    print("Testing Qwen AI client...")
    client = QwenClient()  # Will use OAuth2 flow automatically
    try:
        messages = [
            Message(role="user", content="Explain the quicksort algorithm in Python.")
        ]
        response = client.chat_sync(messages)
        print(f"Successfully received response: {response.content[:100]}...")
        return True
    except Exception as e:
        print(f"Failed to get response from Qwen API: {e}")
        return False


def test_streaming():
    """Test streaming response from Qwen API."""
    print("Testing Qwen AI streaming client...")
    client = QwenClient()  # Will use OAuth2 flow automatically
    try:
        messages = [
            Message(role="user", content="Write a short poem about programming.")
        ]
        print("Streaming response:")
        for chunk in client.stream_chat_sync(messages):
            print(chunk, end="", flush=True)
        print("\nStreaming completed successfully.")
        return True
    except Exception as e:
        print(f"Failed to stream response from Qwen API: {e}")
        return False


if __name__ == "__main__":
    print("Running Qwen Code integration tests...")
    print("=" * 50)
    
    # Test OAuth2 client
    if test_oauth_client():
        print("✓ OAuth2 client test passed")
    else:
        print("✗ OAuth2 client test failed")
    
    print()
    
    # Test Qwen client
    if test_qwen_client():
        print("✓ Qwen client test passed")
    else:
        print("✗ Qwen client test failed")
    
    print()
    
    # Test streaming
    if test_streaming():
        print("✓ Streaming test passed")
    else:
        print("✗ Streaming test failed")
    
    print("=" * 50)
    print("Integration tests completed.")