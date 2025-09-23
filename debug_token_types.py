#!/usr/bin/env python3
"""
Debug script to understand the difference between Qwen OAuth tokens and DashScope API keys
"""

import asyncio
import aiohttp
import json
from qwen_code.auth.credentials import CredentialManager

async def debug_token_types():
    """Debug to understand what type of token we have."""
    print("Debugging token types...")
    
    # Load credentials
    cred_manager = CredentialManager()
    credentials = cred_manager.load_credentials("qwen_oauth")
    
    if not credentials or not credentials.access_token:
        print("[FAIL] No OAuth credentials found")
        return
    
    access_token = credentials.access_token
    
    print(f"Access token length: {len(access_token)}")
    print(f"Access token preview: {access_token[:50]}...")
    
    # Check if it looks like a DashScope API key
    # DashScope API keys typically start with "sk-" and are shorter
    if access_token.startswith("sk-"):
        print("Token looks like a DashScope API key")
    else:
        print("Token looks like a Qwen OAuth token (not a DashScope API key)")
    
    # Try to decode the token to see if it's a JWT
    try:
        # Split the token into parts
        parts = access_token.split('.')
        if len(parts) == 3:
            print("Token looks like a JWT (OAuth token)")
            # Try to decode the header (first part)
            import base64
            header = base64.urlsafe_b64decode(parts[0] + '==')  # Add padding
            header_json = json.loads(header)
            print(f"JWT header: {header_json}")
        else:
            print("Token doesn't look like a JWT")
    except Exception as e:
        print(f"Could not decode token as JWT: {e}")

if __name__ == "__main__":
    asyncio.run(debug_token_types())