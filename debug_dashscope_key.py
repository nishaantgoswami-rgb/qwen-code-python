#!/usr/bin/env python3
"""
Debug script to check if there's an endpoint to get DashScope API key after OAuth
"""

import asyncio
import aiohttp
import json
from qwen_code.auth.credentials import CredentialManager

async def check_for_dashscope_key():
    """Check if there's an endpoint to get DashScope API key after OAuth."""
    print("Checking for DashScope API key endpoint...")
    
    # Load credentials from JSON file
    cred_manager = CredentialManager()
    json_creds = cred_manager.load_tokens_from_json()
    
    if not json_creds or not json_creds.get('access_token'):
        print("[FAIL] No OAuth credentials found in JSON file")
        return
    
    access_token = json_creds['access_token']
    print(f"Using access token: {access_token[:30]}...")
    
    # Try common endpoints that might provide API keys
    possible_endpoints = [
        "https://dashscope.aliyuncs.com/api/v1/user/apikeys",
        "https://chat.qwen.ai/api/v1/user/apikeys",
        "https://dashscope.aliyuncs.com/api/v1/apikeys",
        "https://chat.qwen.ai/api/v1/apikeys"
    ]
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    for endpoint in possible_endpoints:
        print(f"\nTrying endpoint: {endpoint}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=headers) as response:
                    print(f"Response status: {response.status}")
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            print(f"Success! Response: {json.dumps(response_data, indent=2)}")
                            return
                        except:
                            # If it's not JSON, get text
                            response_text = await response.text()
                            print(f"Success! Response (text): {response_text[:200]}...")
                            return
                    elif response.status == 401:
                        error_text = await response.text()
                        print(f"Unauthorized: {error_text[:100]}...")
                    elif response.status == 404:
                        print("Endpoint not found")
                    else:
                        print(f"Other status: {response.status}")
                        if response.status < 500:  # If not a server error, try to read response
                            try:
                                error_text = await response.text()
                                print(f"Response: {error_text[:100]}...")
                            except:
                                pass
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(check_for_dashscope_key())