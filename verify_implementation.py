#!/usr/bin/env python3
"""
Verification script for Qwen OAuth2 client and AI integration.
This script checks if the modules can be imported and instantiated correctly.
"""

import sys
import os

# Add the current directory to Python path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if we can import the modules."""
    print("Testing imports...")
    try:
        # Test importing the OAuth2 client
        from qwen_code.auth.oauth2_client import QwenOAuth2Client
        print("[PASS] QwenOAuth2Client import successful")
        
        # Test importing the AI client
        from qwen_code.ai.client import QwenClient, Message, AIResponse, TokenUsage
        print("[PASS] AI client imports successful")
        
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False

def test_instantiation():
    """Test if we can instantiate the classes."""
    print("Testing instantiation...")
    try:
        # Test instantiating the OAuth2 client
        from qwen_code.auth.oauth2_client import QwenOAuth2Client
        oauth_client = QwenOAuth2Client()
        print("[PASS] QwenOAuth2Client instantiation successful")
        
        # Test instantiating the AI client
        from qwen_code.ai.client import QwenClient, Message
        ai_client = QwenClient()
        print("[PASS] QwenClient instantiation successful")
        
        # Test creating a message
        message = Message(role="user", content="Test message")
        print("[PASS] Message instantiation successful")
        
        return True
    except Exception as e:
        print(f"[FAIL] Instantiation failed: {e}")
        return False

def test_methods():
    """Test if the required methods exist."""
    print("Testing method existence...")
    try:
        from qwen_code.auth.oauth2_client import QwenOAuth2Client
        from qwen_code.ai.client import QwenClient
        
        # Check OAuth2 client methods
        oauth_client = QwenOAuth2Client()
        assert hasattr(oauth_client, 'get_access_token')
        assert hasattr(oauth_client, '_device_flow')
        assert hasattr(oauth_client, '_refresh_token')
        print("[PASS] OAuth2 client methods exist")
        
        # Check AI client methods
        ai_client = QwenClient()
        assert hasattr(ai_client, 'chat_sync')
        assert hasattr(ai_client, 'stream_chat_sync')
        assert hasattr(ai_client, '_get_api_key')
        assert hasattr(ai_client, '_get_headers')
        print("[PASS] AI client methods exist")
        
        return True
    except Exception as e:
        print(f"[FAIL] Method check failed: {e}")
        return False

if __name__ == "__main__":
    print("Running Qwen Code verification tests...")
    print("=" * 50)
    
    # Test imports
    import_result = test_imports()
    print()
    
    # Test instantiation
    instantiation_result = test_instantiation()
    print()
    
    # Test methods
    method_result = test_methods()
    print()
    
    print("=" * 50)
    if import_result and instantiation_result and method_result:
        print("All verification tests passed! The implementation is ready for use.")
        sys.exit(0)
    else:
        print("Some verification tests failed. Please check the implementation.")
        sys.exit(1)