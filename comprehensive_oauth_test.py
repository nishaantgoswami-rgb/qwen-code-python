#!/usr/bin/env python3
"""
Comprehensive test to verify OAuth token usage with DashScope API
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_oauth_token_with_dashscope():
    """Test OAuth token usage with DashScope API using the correct approach."""
    print("Testing OAuth token usage with DashScope API...")
    
    # Load credentials
    with open('C:\\Users\\nisha\\.qwen\\oauth_creds.json', 'r') as f:
        data = json.load(f)
    
    access_token = data.get('access_token')
    print(f"Using access token: {access_token[:30]}...")
    
    # Verify token is still valid
    expiry_date = data.get('expiry_date')
    if expiry_date:
        expiry_datetime = datetime.fromtimestamp(expiry_date / 1000)
        current_datetime = datetime.now()
        print(f"Token expires at: {expiry_datetime}")
        print(f"Current time: {current_datetime}")
        if expiry_datetime < current_datetime:
            print("ERROR: Token has expired!")
            return
    
    # Test the DashScope compatible API endpoint with correct headers
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    endpoint = f"{base_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-DashScope-AuthType": "QWEN_OAUTH",  # This is the key header
        "X-DashScope-CacheControl": "enable"
    }
    
    payload = {
        "model": "qwen3-coder-plus",
        "messages": [
            {
                "role": "user",
                "content": "Hello, this is a test message to verify OAuth token usage."
            }
        ],
        "stream": False
    }
    
    print(f"\nRequest URL: {endpoint}")
    print(f"Request headers: {json.dumps(headers, indent=2)}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=headers, json=payload) as response:
                print(f"\nResponse status: {response.status}")
                print(f"Response headers: {dict(response.headers)}")
                
                response_text = await response.text()
                print(f"Response content: {response_text}")
                
                if response.status == 200:
                    try:
                        response_data = await response.json()
                        print(f"Success! Response JSON: {json.dumps(response_data, indent=2)}")
                    except Exception as e:
                        print(f"Could not parse response as JSON: {e}")
                else:
                    print(f"Error response: {response_text}")
                    
    except Exception as e:
        print(f"Exception during request: {e}")
        import traceback
        traceback.print_exc()

async def test_token_validation():
    """Test if the OAuth token is valid by trying to get user info."""
    print("\n\nTesting OAuth token validation...")
    
    # Load credentials
    with open('C:\\Users\\nisha\\.qwen\\oauth_creds.json', 'r') as f:
        data = json.load(f)
    
    access_token = data.get('access_token')
    
    # Try to validate the token by calling the userinfo endpoint
    validation_endpoints = [
        "https://dashscope.aliyuncs.com/api/v1/oauth2/userinfo",
        "https://chat.qwen.ai/api/v1/oauth2/userinfo"
    ]
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    for endpoint in validation_endpoints:
        print(f"\nTesting validation endpoint: {endpoint}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=headers) as response:
                    print(f"Response status: {response.status}")
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            print(f"Valid token! User info: {json.dumps(response_data, indent=2)}")
                            return True
                        except:
                            response_text = await response.text()
                            print(f"Response (text): {response_text[:200]}...")
                    else:
                        error_text = await response.text()
                        print(f"Error: {error_text[:100]}...")
        except Exception as e:
            print(f"Exception: {e}")
    
    return False

if __name__ == "__main__":
    asyncio.run(test_oauth_token_with_dashscope())
    asyncio.run(test_token_validation())