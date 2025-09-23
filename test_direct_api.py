#!/usr/bin/env python3
"""
Direct API test to see what's wrong with the OAuth token
"""

import sys
import os
import httpx
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from qwen_code.auth.enhanced_oauth2_client import QwenOAuth2Client

def test_direct_api_call():
    """Test making a direct API call to DashScope."""
    print("Testing direct API call to DashScope...")
    
    try:
        # Get OAuth token
        oauth_client = QwenOAuth2Client()
        token = oauth_client.get_access_token()
        print(f"OAuth token: {token[:20]}...")
        
        # Make direct API call
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-DashScope-AuthType": "QWEN_OAUTH",
            "X-DashScope-CacheControl": "enable",
            "X-DashScope-UserAgent": "qwen-code/2.0.0"
        }
        payload = {
            "model": "qwen3-coder-plus",
            "messages": [
                {
                    "role": "user",
                    "content": "Say hello in one word"
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4096
        }
        
        print(f"URL: {url}")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
        
        response = httpx.post(url, json=payload, headers=headers)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Success! Response: {json.dumps(response_data, indent=2)}")
        else:
            error_text = response.text
            print(f"Error response: {error_text}")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_api_call()