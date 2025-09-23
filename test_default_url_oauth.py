#!/usr/bin/env python3
"""
Test using default DashScope URL with proper OAuth headers
"""

import sys
import os
import aiohttp
import asyncio
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from qwen_code.auth.enhanced_oauth2_client import QwenOAuth2Client

async def test_default_url_with_oauth():
    """Test using default DashScope URL with OAuth headers."""
    print("Testing default DashScope URL with OAuth headers...")
    
    try:
        # Get OAuth token
        oauth_client = QwenOAuth2Client()
        token = oauth_client.get_access_token()
        print(f"OAuth token: {token[:20]}...")
        
        # Use default DashScope URL
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        print(f"URL: {url}")
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-DashScope-AuthType": "QWEN_OAUTH",
            "X-DashScope-CacheControl": "enable",
            "X-DashScope-UserAgent": "qwen-code/2.0.0"
        }
        print(f"Headers: {headers}")
        
        # Prepare payload
        payload = {
            "model": "qwen3-coder-plus",
            "messages": [
                {
                    "role": "user",
                    "content": "Say hello in one word"
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4096
        }
        print(f"Payload: {payload}")
        
        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                print(f"Response status: {response.status}")
                print(f"Response headers: {dict(response.headers)}")
                
                if response.status == 200:
                    response_data = await response.json()
                    print(f"Success! Response: {json.dumps(response_data, indent=2)}")
                else:
                    error_text = await response.text()
                    print(f"Error response: {error_text}")
                    
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_default_url_with_oauth())