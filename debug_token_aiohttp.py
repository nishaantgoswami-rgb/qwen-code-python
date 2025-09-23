#!/usr/bin/env python3
"""
Debug script for Qwen OAuth using aiohttp like the provider
"""

import asyncio
import aiohttp
import base64
import json
import hashlib
import os

async def debug_token_polling_aiohttp():
    """Debug token polling using aiohttp."""
    print("Debugging token polling with aiohttp...")
    
    # Token endpoint
    TOKEN_URL = "https://chat.qwen.ai/api/v1/oauth2/token"
    CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"
    
    # Generate a PKCE pair for testing
    verifier = "test_verifier_1234567890"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    
    # Use an invalid device code to trigger an error response
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": CLIENT_ID,
        "device_code": "invalid_device_code_test_1234567890",
        "code_verifier": verifier,
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Qwen-Code-CLI/1.0"
    }
    
    print(f"Request URL: {TOKEN_URL}")
    print(f"Request Data: {data}")
    print(f"Request Headers: {headers}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(TOKEN_URL, data=data, headers=headers, allow_redirects=False) as response:
                print(f"Response Status: {response.status}")
                print(f"Response Headers: {dict(response.headers)}")
                
                # Get response content
                content = await response.text()
                print(f"Response Content: {content}")
                
                # Check if it's a redirect
                if response.status in [301, 302, 303, 307, 308]:
                    location = response.headers.get('location', 'Unknown')
                    print(f"Redirect to: {location}")
                    return None
                    
                if response.status == 200:
                    try:
                        json_response = await response.json()
                        print(f"JSON Response: {json_response}")
                        return json_response
                    except Exception as e:
                        print(f"Failed to decode JSON: {e}")
                        return None
                else:
                    print(f"Request failed with status {response.status}")
                    try:
                        # Try to parse error response as JSON
                        json_response = await response.json()
                        print(f"Error JSON Response: {json_response}")
                        return json_response
                    except Exception:
                        print("Could not decode error response as JSON")
                        return None
    except Exception as e:
        print(f"Request failed with exception: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(debug_token_polling_aiohttp())