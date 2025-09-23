#!/usr/bin/env python3
"""
Test using the resource_url as the endpoint
"""

import asyncio
import aiohttp
import json

async def test_with_resource_url():
    """Test using the resource_url from credentials as the endpoint."""
    print("Testing with resource_url as endpoint...")
    
    # Load credentials
    with open('C:\\\\Users\\\\nisha\\\\.qwen\\\\oauth_creds.json', 'r') as f:
        data = json.load(f)
    
    api_key = data.get('access_token')  # This is the OAuth token
    resource_url = data.get('resource_url')
    
    print(f"Using API key (OAuth token): {api_key[:30]}...")
    print(f"Using resource URL: {resource_url}")
    
    # Try using the resource URL as the base URL
    if resource_url:
        base_url = f"https://{resource_url}/api/v1"
        endpoint = f"{base_url}/chat/completions"
        
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
    else:
        print("No resource_url found in credentials")

if __name__ == "__main__":
    asyncio.run(test_with_resource_url())