#!/usr/bin/env python3
"""
Test different endpoints to see which one works with OAuth tokens
"""

import asyncio
import aiohttp
import json

async def test_different_endpoints():
    """Test different endpoints to see which one works with OAuth tokens."""
    print("Testing different endpoints with OAuth tokens...")
    
    # Load credentials
    with open('C:\\Users\\nisha\\.qwen\\oauth_creds.json', 'r') as f:
        data = json.load(f)
    
    api_key = data.get('access_token')  # This is the OAuth token
    
    print(f"Using API key (OAuth token): {api_key[:30]}...")
    
    # Test different endpoints
    endpoints = [
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "https://dashscope.aliyuncs.com/api/v1/chat/completions",
        "https://chat.qwen.ai/api/v1/chat/completions"
    ]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-AuthType": "QWEN_OAUTH",
        "X-DashScope-CacheControl": "enable"
    }
    
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
    
    for endpoint in endpoints:
        print(f"\n--- Testing endpoint: {endpoint} ---")
        print(f"Request headers: {json.dumps(headers, indent=2)}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=headers, json=payload) as response:
                    print(f"Response status: {response.status}")
                    print(f"Response headers: {dict(response.headers)}")
                    
                    response_text = await response.text()
                    print(f"Response content: {response_text}")
                    
                    if response.status == 200:
                        response_data = await response.json()
                        print(f"Success! Response: {json.dumps(response_data, indent=2)}")
                        return  # If one works, we're done
                    else:
                        print(f"Error: {response_text}")
                        
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_different_endpoints())