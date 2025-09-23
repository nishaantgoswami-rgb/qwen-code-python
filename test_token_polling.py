#!/usr/bin/env python3
"""
Simple OAuth token polling test
"""

import httpx
import json

def test_token_polling():
    """Test token polling with a device code."""
    print("Testing token polling...")
    
    # Token endpoint
    TOKEN_URL = "https://chat.qwen.ai/api/v1/oauth2/token"
    CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"
    
    # Use an invalid device code to see the error response
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": CLIENT_ID,
        "device_code": "invalid_device_code",
        "code_verifier": "invalid_verifier",
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
    test_token_polling()