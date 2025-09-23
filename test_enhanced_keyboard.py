#!/usr/bin/env python3
\"\"\"Test script to verify enhanced keyboard handler functionality.\"\"\"

import sys
import asyncio
from qwen_code.cli.enhanced_keyboard_handler import EnhancedKeyboardHandler, detect_terminal_capabilities

def test_basic_functionality():
    \"\"\"Test basic functionality of the enhanced keyboard handler.\"\"\"
    print(\"Testing EnhancedKeyboardHandler...\")
    
    # Create an instance
    handler = EnhancedKeyboardHandler()
    
    # Test command registration
    handler.register_command(\"/test\", \"Test command for verification\")
    print(f\"Registered commands: {handler.commands}\")
    
    # Test terminal capabilities detection
    capabilities = detect_terminal_capabilities()
    print(f\"Terminal capabilities: {capabilities}\")
    
    return True

def test_input_functionality():
    \"\"\"Test input functionality.\"\"\"
    print(\"\\nTesting input functionality. Type some text and press Enter...\")
    
    handler = EnhancedKeyboardHandler()
    
    try:
        user_input = handler.get_input_with_features()
        print(f\"You entered: {user_input}\")
        
        # Test help display
        print(\"\\nTesting help display...\")
        handler.show_help()
        
    except KeyboardInterrupt:
        print(\"\\nTest interrupted by user.\")
    except Exception as e:
        print(f\"Error during input test: {e}\")
        return False
    
    return True

async def main():
    \"\"\"Main test function.\"\"\"
    print(\"Enhanced Keyboard Handler Test Suite\")
    print(\"=\" * 40)
    
    # Test basic functionality
    if not test_basic_functionality():
        print(\"Basic functionality test failed.\")
        sys.exit(1)
    
    # Test input functionality
    if not test_input_functionality():
        print(\"Input functionality test failed.\")
        sys.exit(1)
    
    print(\"\\nAll tests passed!\")

if __name__ == \"__main__\":
    asyncio.run(main())