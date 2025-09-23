"""
Comprehensive test script to identify the correct DashScope token exchange endpoint.
"""

import asyncio
import httpx
import json
from qwen_code.auth.credentials import CredentialManager


async def find_token_exchange_endpoint():
    """Try to find the correct endpoint for exchanging OAuth tokens for DashScope API keys."""
    print("Searching for the correct DashScope token exchange endpoint...")
    
    # Load credentials
    cred_manager = CredentialManager()
    credentials = cred_manager.load_credentials("qwen_oauth")
    
    if not credentials or not credentials.access_token:
        # Try JSON file as fallback
        json_creds = cred_manager.load_tokens_from_json()
        if not json_creds or not json_creds.get('access_token'):
            print("[FAIL] No OAuth credentials found")
            return
        access_token = json_creds['access_token']
    else:
        access_token = credentials.access_token
    
    print(f"Using OAuth token: {access_token[:20]}...")
    
    # List of possible endpoints to try
    possible_endpoints = [
        # DashScope endpoints
        "https://dashscope.aliyuncs.com/api/v1/tokens/from-qwen-oauth",
        "https://dashscope.aliyuncs.com/api/v1/user/apikeys/exchange",
        "https://dashscope.aliyuncs.com/api/v1/apikeys/exchange",
        "https://dashscope.aliyuncs.com/api/v1/user/apikeys",
        "https://dashscope.aliyuncs.com/api/v1/apikeys",
        
        # Qwen endpoints
        "https://chat.qwen.ai/api/v1/dashscope/key",
        "https://chat.qwen.ai/api/v1/user/apikeys",
        "https://chat.qwen.ai/api/v1/apikeys",
        
        # Aliyun endpoints
        "https://dashscope.console.aliyun.com/api/v1/user/apikeys",
        "https://dashscope.console.aliyun.com/api/v1/apikeys",
    ]
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "Qwen-Code-CLI/1.0"
    }
    
    found_endpoint = None
    found_response = None
    
    for endpoint in possible_endpoints:
        print(f"\nTrying endpoint: {endpoint}")
        try:
            async with httpx.AsyncClient() as client:
                # Try POST first
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json={}
                )
                
                print(f"  POST response status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        print(f"  Success! POST response: {json.dumps(response_data, indent=2)[:200]}...")
                        found_endpoint = endpoint
                        found_response = response_data
                        break
                    except Exception as e:
                        response_text = response.text
                        print(f"  Success! POST response (text): {response_text[:200]}...")
                        found_endpoint = endpoint
                        found_response = response_text
                        break
                elif response.status_code in [404, 405]:
                    # Try GET if POST failed with 404 or 405
                    response = await client.get(
                        endpoint,
                        headers=headers
                    )
                    
                    print(f"  GET response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            print(f"  Success! GET response: {json.dumps(response_data, indent=2)[:200]}...")
                            found_endpoint = endpoint
                            found_response = response_data
                            break
                        except Exception as e:
                            response_text = response.text
                            print(f"  Success! GET response (text): {response_text[:200]}...")
                            found_endpoint = endpoint
                            found_response = response_text
                            break
                else:
                    # For other status codes, try to read response
                    if response.status_code < 500:
                        try:
                            error_text = response.text
                            print(f"  Response: {error_text[:100]}...")
                        except:
                            pass
        except Exception as e:
            print(f"  Exception: {e}")
    
    if found_endpoint:
        print(f"\n[SUCCESS] Found working endpoint: {found_endpoint}")
        print(f"Response: {json.dumps(found_response, indent=2) if isinstance(found_response, dict) else found_response}")
    else:
        print("\n[FAIL] Could not find a working endpoint for token exchange")


if __name__ == "__main__":
    asyncio.run(find_token_exchange_endpoint())
