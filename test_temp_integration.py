#!/usr/bin/env python3
"""
Test script for Qwen OAuth2 client and AI integration.
This version uses a temporary OAuth2 client that doesn't save tokens to a file.
"""

import sys
import os

# Add the current directory to Python path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our temporary OAuth2 client
from qwen_code.auth.temp_oauth2_client import QwenOAuth2Client
from qwen_code.ai.client import QwenClient, Message


def test_oauth_client():
    """Test the OAuth2 client."""
    print("Testing Qwen OAuth2 client...")
    try:
        client = QwenOAuth2Client()
        token = client.get_access_token()
        print(f"Successfully obtained access token: {token[:20]}...")
        return True, token
    except Exception as e:
        print(f"Failed to obtain access token: {e}")
        return False, None


def test_qwen_client(token):
    """Test the Qwen AI client with a provided token."""
    print("Testing Qwen AI client...")
    try:
        # Create QwenClient with the provided token
        client = QwenClient(api_key=token, is_oauth_token=True)
        messages = [
            Message(role="user", content="Say hello world in Python.")
        ]
        response = client.chat_sync(messages)
        print(f"Successfully received response: {response.content[:100]}...")
        return True
    except Exception as e:
        print(f"Failed to get response from Qwen API: {e}")
        return False


def test_streaming(token):
    """Test streaming response from Qwen API with a provided token."""
    print("Testing Qwen AI streaming client...")
    try:
        # Create QwenClient with the provided token
        client = QwenClient(api_key=token, is_oauth_token=True)
        messages = [
            Message(role="user", content="Count from 1 to 5.")
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
    print("Running Qwen Code integration tests (temporary version)...")
    print("=" * 50)
    
    # Test OAuth2 client
    oauth_result, token = test_oauth_client()
    if oauth_result:
        print("✓ OAuth2 client test passed")
    else:
        print("✗ OAuth2 client test failed")
    
    print()
    
    # Test Qwen client (only if OAuth succeeded)
    qwen_result = False
    if oauth_result:
        qwen_result = test_qwen_client(token)
        if qwen_result:
            print("✓ Qwen client test passed")
        else:
            print("✗ Qwen client test failed")
    else:
        print("Skipping Qwen client test due to OAuth failure")
    
    print()
    
    # Test streaming (only if OAuth succeeded)
    streaming_result = False
    if oauth_result:
        streaming_result = test_streaming(token)
        if streaming_result:
            print("✓ Streaming test passed")
        else:
            print("✗ Streaming test failed")
    else:
        print("Skipping streaming test due to OAuth failure")
    
    print("=" * 50)
    print("Integration tests completed.")
    
    # Return success only if all tests passed
    if oauth_result and qwen_result and streaming_result:
        sys.exit(0)
    else:
        sys.exit(1)