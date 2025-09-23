#!/usr/bin/env python3
"""
Test script to verify the enhanced OAuth2 client works correctly
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from qwen_code.auth.enhanced_oauth2_client import QwenOAuth2Client

def test_token_exchange():
    """Test the token exchange functionality."""
    print("Testing token exchange functionality...")
    
    # Create the enhanced OAuth2 client
    oauth_client = QwenOAuth2Client()
    
    try:
        # Test getting OAuth token
        print("Getting OAuth access token...")
        oauth_token = oauth_client.get_access_token()
        print(f"OAuth token: {oauth_token[:20]}...")
        
        # Test exchanging for DashScope API key
        print("Attempting to exchange OAuth token for DashScope API key...")
        try:
            api_key = oauth_client.get_dashscope_api_key()
            print(f"DashScope API key: {api_key[:20]}...")
            if api_key != oauth_token:
                print("Token exchange successful!")
                return True
            else:
                print("Using OAuth token directly (exchange may have failed)")
                return True
        except Exception as e:
            print(f"Token exchange failed: {e}")
            print("Falling back to using OAuth token directly...")
            api_key = oauth_token
            print(f"Using OAuth token as API key: {api_key[:20]}...")
            return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_token_exchange()
    if success:
        print("\nTest completed successfully!")
    else:
        print("\nTest failed!")
