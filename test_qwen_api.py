#!/usr/bin/env python3
"""
Direct API test script for Qwen API with OAuth token
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_qwen_api():
    """Test the Qwen API directly with OAuth token."""
    print("Testing Qwen API directly...")
    
    # Load credentials
    with open('C:\\Users\\nisha\\.qwen\\oauth_creds.json', 'r') as f:
        data = json.load(f)
    
    access_token = data.get('access_token')
    print(f"Using access token: {access_token[:30]}...")
    
    # API endpoint
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    endpoint = f"{base_url}/chat/completions"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-DashScope-AuthType": "QWEN_OAUTH",
        "X-DashScope-CacheControl": "enable"
    }
    
    # Payload
    payload = {
        "model": "qwen3-coder-plus",
        "messages": [
            {
                "role": "user",
                "content": "Hello, this is a test message."
            }
        ],
        "stream": False
    }
    
    print(f"Request URL: {endpoint}")
    print(f"Request headers: {headers}")
    print(f"Request payload: {payload}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=headers, json=payload) as response:
                print(f"Response status: {response.status}")
                response_text = await response.text()
                print(f"Response headers: {dict(response.headers)}")
                print(f"Response content: {response_text}")
                
                if response.status == 200:
                    response_data = await response.json()
                    print(f"Response JSON: {json.dumps(response_data, indent=2)}")
                else:
                    print(f"Error response: {response_text}")
                    
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_qwen_api())