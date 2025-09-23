#!/usr/bin/env python3
"""
Fix credentials synchronization between database and JSON file
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from qwen_code.auth.credentials import CredentialManager
import json

def fix_credentials():
    """Fix credentials synchronization."""
    print("Fixing credentials synchronization...")
    
    # Load credentials from JSON file (which seems to be the correct one)
    cred_manager = CredentialManager()
    json_creds = cred_manager.load_tokens_from_json()
    
    print(f"JSON credentials: {json_creds}")
    
    if not json_creds or not json_creds.get('access_token'):
        print("No valid credentials found in JSON file!")
        return
    
    # Update database credentials with JSON credentials
    from qwen_code.auth.credentials import Credentials
    from datetime import datetime, timedelta
    
    # Calculate expiration time
    expiry_date = json_creds.get('expiry_date')
    expires_at = None
    if expiry_date:
        # Convert milliseconds to seconds
        expires_at = datetime.fromtimestamp(expiry_date / 1000)
    
    # Create credentials object
    credentials = Credentials(
        provider="qwen_oauth",
        access_token=json_creds['access_token'],
        refresh_token=json_creds.get('refresh_token'),
        expires_at=expires_at.isoformat() if expires_at else None
    )
    
    # Store in database
    cred_manager.store_credentials(credentials)
    print("Credentials synchronized successfully!")
    
    # Verify
    db_creds = cred_manager.load_credentials("qwen_oauth")
    print(f"Updated database credentials: {db_creds}")

if __name__ == "__main__":
    fix_credentials()