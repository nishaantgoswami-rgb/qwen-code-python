#!/usr/bin/env python3
"""
Debug script to check if Qwen OAuth token can be used to get a DashScope API key
"""

import asyncio
import aiohttp
import json
from qwen_code.auth.credentials import CredentialManager

async def check_token_exchange():
    """Check if we can exchange Qwen OAuth token for DashScope API key."""
    print("Checking if Qwen OAuth token can be exchanged for DashScope API key...")
    
    # Load credentials
    cred_manager = CredentialManager()
    credentials = cred_manager.load_credentials("qwen_oauth")
    
    if not credentials or not credentials.access_token:
        print("[FAIL] No OAuth credentials found")
        return
    
    access_token = credentials.access_token
    print(f"Qwen OAuth token: {access_token[:30]}...")
    
    # Try to see if there's an endpoint to exchange tokens
    # This is speculative - let's try a few common patterns
    possible_endpoints = [
        "https://dashscope.aliyuncs.com/api/v1/token/exchange",
        "https://dashscope.aliyuncs.com/api/v1/apikey",
        "https://chat.qwen.ai/api/v1/dashscope/key",
        "https://chat.qwen.ai/api/v1/apikey"
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
                        response_data = await response.json()
                        print(f"Success! Response: {response_data}")
                        return
                    elif response.status == 401:
                        error_text = await response.text()
                        print(f"Unauthorized: {error_text[:100]}...")
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
    asyncio.run(check_token_exchange())