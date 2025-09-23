#!/usr/bin/env python3
"""Test script for the keyboard handler functionality."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qwen_code.cli.keyboard_handler import KeyboardHandler

def test_keyboard_handler():
    """Test the keyboard handler functionality."""
    print("Testing KeyboardHandler...")
    handler = KeyboardHandler()
    
    # Test command list
    print("Available commands:", handler.commands)
    
    # Test command descriptions
    print("Command descriptions:")
    for cmd, desc in handler.command_descriptions.items():
        print(f"  {cmd}: {desc}")
    
    print("\nKeyboard handler initialized successfully!")
    print("Note: Full functionality requires running in the actual CLI environment.")

if __name__ == "__main__":
    test_keyboard_handler()