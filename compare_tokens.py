#!/usr/bin/env python3
"""
Test script to see how DashScope API keys should look vs OAuth tokens
"""

import json
from qwen_code.auth.credentials import CredentialManager

def compare_token_formats():
    """Compare the format of OAuth tokens vs API keys."""
    print("Comparing token formats...")
    
    # Load credentials from JSON file (OAuth token)
    cred_manager = CredentialManager()
    json_creds = cred_manager.load_tokens_from_json()
    
    if json_creds and json_creds.get('access_token'):
        oauth_token = json_creds['access_token']
        print(f"OAuth token: {oauth_token}")
        print(f"OAuth token length: {len(oauth_token)}")
        print(f"OAuth token starts with: {oauth_token[:10]}")
        print(f"OAuth token ends with: {oauth_token[-10:]}")
    
    # Load from encrypted database
    credentials = cred_manager.load_credentials("qwen_oauth")
    if credentials and credentials.access_token:
        db_token = credentials.access_token
        print(f"\nDB token: {db_token}")
        print(f"DB token length: {len(db_token)}")
        print(f"DB token starts with: {db_token[:10]}")
        print(f"DB token ends with: {db_token[-10:]}")
    
    # Compare with a typical DashScope API key format
    # DashScope API keys typically start with "sk-" and are shorter
    print("\nTypical DashScope API key format:")
    print("  Starts with: sk-")
    print("  Length: ~40-50 characters")
    print("  Example: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

if __name__ == "__main__":
    compare_token_formats()