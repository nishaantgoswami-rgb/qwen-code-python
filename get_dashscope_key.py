#!/usr/bin/env python3
"""
Test to see if we can get a DashScope API key using the OAuth token
"""

import asyncio
import aiohttp
import json
from qwen_code.auth.credentials import CredentialManager

async def try_to_get_api_key():
    """Try to get a DashScope API key using the OAuth token."""
    print("Trying to get DashScope API key using OAuth token...")
    
    # Load credentials from JSON file
    cred_manager = CredentialManager()
    json_creds = cred_manager.load_tokens_from_json()
    
    if not json_creds or not json_creds.get('access_token'):
        print("[FAIL] No OAuth credentials found in JSON file")
        return
    
    access_token = json_creds['access_token']
    print(f"Using access token: {access_token[:30]}...")
    
    # Try to get API key from portal
    portal_url = json_creds.get('resource_url', 'portal.qwen.ai')
    if not portal_url.startswith('http'):
        portal_url = f'https://{portal_url}'
    
    print(f"Portal URL: {portal_url}")
    
    # Try to get API key endpoint
    api_key_endpoints = [
        f"{portal_url}/api/v1/apikeys",
        f"{portal_url}/api/v1/user/apikeys",
        "https://dashscope.console.aliyun.com/api/v1/apikeys",
        "https://dashscope.aliyuncs.com/api/v1/user/apikeys"
    ]
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    for endpoint in api_key_endpoints:
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
    asyncio.run(try_to_get_api_key())