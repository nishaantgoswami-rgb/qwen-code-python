#!/usr/bin/env python3
"""
Debug script for Qwen Code chat functionality
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from qwen_code.app import QwenCodeApplication
from qwen_code.ai.client import QwenClient, Message
from qwen_code.config.settings import Config
from qwen_code.auth.credentials import CredentialManager

async def debug_chat():
    """Debug the chat functionality."""
    print("Debugging chat functionality...")
    
    # Initialize the application
    app = QwenCodeApplication()
    await app.initialize()
    
    # Get the configuration
    config = Config()
    await config.load()
    
    print(f"Auth provider: {config.auth_provider}")
    print(f"Providers config: {config.providers}")
    
    # Try to get credentials
    api_key = None
    is_oauth_token = False
    
    if config.auth_provider == "qwen_oauth":
        # Try to get from credentials manager (encrypted database)
        cred_manager = CredentialManager()
        credentials = cred_manager.load_credentials("qwen_oauth")
        print(f"Database credentials: {credentials}")
        
        if credentials and credentials.access_token:
            api_key = credentials.access_token
            is_oauth_token = True
            print(f"Using access token from database: {api_key[:20]}...")
        else:
            # Fallback to JSON file
            json_creds = cred_manager.load_tokens_from_json()
            print(f"JSON credentials: {json_creds}")
            
            if json_creds and json_creds.get('access_token'):
                api_key = json_creds['access_token']
                is_oauth_token = True
                print(f"Using access token from JSON: {api_key[:20]}...")
    
    if not api_key:
        print("ERROR: No API key found!")
        return
    
    # Create AI client
    print(f"Creating QwenClient with is_oauth_token={is_oauth_token}")
    ai_client = QwenClient(api_key=api_key, model="qwen3-coder-plus", is_oauth_token=is_oauth_token)
    
    # Test chat
    print("Testing chat...")
    messages = [Message(role="user", content="Hello, this is a test message.")]
    
    try:
        response = await ai_client.chat(messages)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error during chat: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_chat())