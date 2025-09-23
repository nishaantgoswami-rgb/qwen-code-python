#!/usr/bin/env python3
"""
Debug script to verify Authorization header format and exact content
"""

import asyncio
from qwen_code.auth.credentials import CredentialManager
from qwen_code.ai.client import QwenClient, Message

async def debug_auth_header():
    """Debug the Authorization header format and content."""
    print("Debugging Authorization header...")
    
    # Load credentials
    cred_manager = CredentialManager()
    credentials = cred_manager.load_credentials("qwen_oauth")
    
    if credentials and credentials.access_token:
        print("[PASS] Found OAuth credentials")
        print(f"Access token length: {len(credentials.access_token)}")
        print(f"Access token preview: {credentials.access_token[:50]}...")
        
        # Create AI client with OAuth token
        ai_client = QwenClient(
            api_key=credentials.access_token,
            is_oauth_token=True
        )
        
        # Show exactly what the Authorization header will look like
        auth_header = f"Bearer {credentials.access_token}"
        print(f"Authorization header: {auth_header}")
        print(f"Authorization header length: {len(auth_header)}")
        
        # Test with a mock request to see what's being sent
        print("\nTesting with a simple request to see headers...")
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Just make a request to see what headers are being sent
                headers = {
                    "Authorization": auth_header,
                    "Content-Type": "application/json"
                }
                
                print(f"Headers being sent: {headers}")
                
                # Make a simple request to see the response
                async with session.get(
                    f"{ai_client.base_url}/models",  # This should be a valid endpoint
                    headers=headers
                ) as response:
                    print(f"Response status: {response.status}")
                    print(f"Response headers: {dict(response.headers)}")
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Error response: {error_text[:200]}...")
                        
        except Exception as e:
            print(f"Exception during request: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("[FAIL] No OAuth credentials found")

if __name__ == "__main__":
    asyncio.run(debug_auth_header())