#!/usr/bin/env python3
"""
Debug script to see exactly what headers and URL are being used
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from qwen_code.ai.client import QwenClient

def debug_qwen_client():
    """Debug the QwenClient to see headers and URL."""
    print("Debugging QwenClient...")
    
    try:
        # Create QwenClient without providing API key
        client = QwenClient()
        
        # Check what API key is being used
        api_key = client._get_api_key()
        print(f"API key: {api_key[:20]}...")
        
        # Check what headers are being used
        headers = client._get_headers()
        print(f"Headers: {headers}")
        
        # Check the base URL
        print(f"Base URL: {client.base_url}")
        
        print("Debug completed!")
        
    except Exception as e:
        print(f"Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_qwen_client()