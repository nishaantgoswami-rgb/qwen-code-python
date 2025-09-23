#!/usr/bin/env python3
"""
Test script to verify the QwenClient works correctly with enhanced OAuth2 client
"""

import sys
import os
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from qwen_code.ai.client import QwenClient, Message

async def test_qwen_client():
    """Test the QwenClient with enhanced OAuth2 client."""
    print("Testing QwenClient with enhanced OAuth2 client...")
    
    try:
        # Create QwenClient without providing API key
        # This should use our enhanced OAuth2 client automatically
        client = QwenClient()
        
        # Test sending a simple message
        messages = [Message(role="user", content="Say hello in one word")]
        print("Sending test message...")
        response = await client.chat(messages)
        print(f"Response: {response.content}")
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_qwen_client())