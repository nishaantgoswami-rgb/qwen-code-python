#!/usr/bin/env python3
"""
Debug script for Qwen OAuth implementation
"""

import httpx
import base64
import os
import json
import hashlib
import time

def generate_pkce_pair():
    """Generate PKCE verifier and challenge."""
    # Create a high-entropy verifier
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge

def debug_device_code_request():
    """Debug device code request."""
    print("Debugging device code request...")
    
    # Generate PKCE pair
    verifier, challenge = generate_pkce_pair()
    
    # Device code endpoint
    DEVICE_CODE_URL = "https://chat.qwen.ai/api/v1/oauth2/device/code"
    CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"
    SCOPE = "openid profile email model.completion"
    
    data = {
        "client_id": CLIENT_ID,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Qwen-Code-CLI/1.0"
    }
    
    print(f"Request URL: {DEVICE_CODE_URL}")
    print(f"Request Data: {data}")
    print(f"Request Headers: {headers}")
    
    try:
        response = httpx.post(DEVICE_CODE_URL, data=data, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text}")
        
        if response.status_code == 200:
            try:
                json_response = response.json()
                print(f"JSON Response: {json_response}")
                return json_response, verifier
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
                return None, None
        else:
            print(f"Request failed with status {response.status_code}")
            return None, None
    except Exception as e:
        print(f"Request failed with exception: {e}")
        return None, None

def debug_token_polling(device_code, verifier):
    """Debug token polling."""
    print("\nDebugging token polling...")
    
    # Token endpoint
    TOKEN_URL = "https://chat.qwen.ai/api/v1/oauth2/token"
    CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"
    
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": CLIENT_ID,
        "device_code": device_code,
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
        response = httpx.post(TOKEN_URL, data=data, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text}")
        
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
                json_response = response.json()
                print(f"Error JSON Response: {json_response}")
            except json.JSONDecodeError:
                print("Could not decode error response as JSON")
            return None
    except Exception as e:
        print(f"Request failed with exception: {e}")
        return None

if __name__ == "__main__":
    # First get device code
    device_response, verifier = debug_device_code_request()
    
    if device_response and verifier:
        print(f"\nDevice code: {device_response['device_code']}")
        print(f"User code: {device_response['user_code']}")
        print(f"Verification URI: {device_response['verification_uri_complete']}")
        print("\nPlease visit the verification URI and authorize the application.")
        input("Press Enter after authorizing...")
        
        # Then test token polling
        debug_token_polling(device_response['device_code'], verifier)
