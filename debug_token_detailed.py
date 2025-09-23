#!/usr/bin/env python3
"""
Debug script for Qwen OAuth token polling with detailed response info
"""

import httpx
import base64
import os
import json
import hashlib

def debug_token_polling_detailed():
    """Debug token polling with detailed response information."""
    print("Debugging token polling with detailed response info...")
    
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
        # Don't follow redirects to see if that's the issue
        response = httpx.post(TOKEN_URL, data=data, headers=headers, follow_redirects=False)
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response URL: {response.url}")
        print(f"Response Content: {response.text}")
        
        # Check if it's a redirect
        if response.status_code in [301, 302, 303, 307, 308]:
            print(f"Redirect to: {response.headers.get('location', 'Unknown')}")
            return None
            
        if response.status_code == 200:
            try:
                json_response = response.json()
                print(f"JSON Response: {json_response}")
                return json_response
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
                return None
        else:
            print(f"Request failed with status {response.status_code}")
            try:
                # Try to parse error response as JSON
                json_response = response.json()
                print(f"Error JSON Response: {json_response}")
                return json_response
            except json.JSONDecodeError:
                print("Could not decode error response as JSON")
                return None
    except Exception as e:
        print(f"Request failed with exception: {e}")
        return None

if __name__ == "__main__":
    debug_token_polling_detailed()