#!/usr/bin/env python3
"""
Debug script to see what the OAuth token response looks like
"""

import json
from qwen_code.auth.credentials import CredentialManager

def debug_oauth_token_response():
    """Debug to see what the OAuth token response looks like."""
    print("Debugging OAuth token response...")
    
    # Load credentials from JSON file (the format that the OAuth client uses)
    cred_manager = CredentialManager()
    json_creds = cred_manager.load_tokens_from_json()
    
    if not json_creds:
        print("[FAIL] No OAuth credentials found in JSON file")
        return
    
    print("OAuth token response from JSON file:")
    print(json.dumps(json_creds, indent=2))
    
    # Also check from encrypted database
    credentials = cred_manager.load_credentials("qwen_oauth")
    if credentials:
        print("\nCredentials from encrypted database:")
        creds_dict = {
            "provider": credentials.provider,
            "access_token": credentials.access_token[:30] + "..." if credentials.access_token else None,
            "refresh_token": credentials.refresh_token[:30] + "..." if credentials.refresh_token else None,
            "expires_at": credentials.expires_at,
            "metadata": credentials.metadata
        }
        print(json.dumps(creds_dict, indent=2))

if __name__ == "__main__":
    debug_oauth_token_response()