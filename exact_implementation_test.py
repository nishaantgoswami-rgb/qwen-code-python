#!/usr/bin/env python3
"""
Test that exactly matches the TypeScript implementation
"""

import asyncio
import aiohttp
import json

async def test_exact_implementation():
    """Test using the exact same approach as the TypeScript implementation."""
    print("Testing exact TypeScript implementation approach...")
    
    # Load credentials
    with open('C:\\Users\\nisha\\.qwen\\oauth_creds.json', 'r') as f:
        data = json.load(f)
    
    api_key = data.get('access_token')  # This is the OAuth token
    print(f"Using API key (OAuth token): {api_key[:30]}...")
    
    # Use the exact same base URL as TypeScript
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    endpoint = f"{base_url}/chat/completions"
    
    # Use the exact same headers as TypeScript
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-AuthType": "QWEN_OAUTH",  # From authType in config
        "X-DashScope-CacheControl": "enable"
    }
    
    # Use the exact same payload structure as TypeScript
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
    print(f"Request headers: {json.dumps(headers, indent=2)}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
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
                else:
                    print(f"Error: {response_text}")
                    
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_exact_implementation())