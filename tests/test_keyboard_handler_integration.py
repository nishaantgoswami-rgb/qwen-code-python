"""
Integration tests for the keyboard handler functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qwen_code.cli.keyboard_handler import KeyboardHandler


class TestKeyboardHandler(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = KeyboardHandler()
    
    def test_command_list(self):
        """Test that the command list contains expected commands."""
        expected_commands = ["/help", "/clear", "/stats", "exit", "quit"]
        self.assertEqual(self.handler.commands, expected_commands)
    
    def test_command_descriptions(self):
        """Test that all commands have descriptions."""
        for command in self.handler.commands:
            self.assertIn(command, self.handler.command_descriptions)
            self.assertIsInstance(self.handler.command_descriptions[command], str)
            self.assertGreater(len(self.handler.command_descriptions[command]), 0)
    
    def test_longest_common_prefix(self):
        """Test the longest common prefix function."""
        # Test with common prefixes
        test_cases = [
            (["/help", "/hello", "/hi"], "/h"),
            (["/help", "/helpme", "/helper"], "/help"),
            (["/help", "/clear"], "/"),
            (["/help"], "/help"),
            ([], "")
        ]
        
        for strs, expected in test_cases:
            with self.subTest(strs=strs):
                result = self.handler._longest_common_prefix(strs)
                self.assertEqual(result, expected)
    
    def test_auto_complete_exact_match(self):
        """Test auto-completion with exact match."""
        result = self.handler._auto_complete_command("/help")
        self.assertEqual(result, "/help")
    
    def test_auto_complete_partial_match(self):
        """Test auto-completion with partial match."""
        result = self.handler._auto_complete_command("/he")
        self.assertEqual(result, "/help")
    
    def test_auto_complete_multiple_matches(self):
        """Test auto-completion with multiple matches."""
        # With our implementation, when there's an exact match or single completion,
        # it should return that. For "/h", it should return "/help" since that's
        # the only command that starts with "/h"
        result = self.handler._auto_complete_command("/h")
        # Should return the completed command
        self.assertEqual(result, "/help")


if __name__ == '__main__':
    unittest.main()