"""Unit tests for terminal manager."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from ptsd_agent.ui.terminal import TerminalManager


class TestTerminalManager(unittest.TestCase):
    """Test cases for TerminalManager class."""
    
    def test_initialization(self):
        """Test terminal manager initializes correctly."""
        term = TerminalManager()
        self.assertIsNotNone(term.width)
        self.assertIsNotNone(term.height)
        self.assertGreater(term.width, 0)
        self.assertGreater(term.height, 0)
    
    def test_get_size(self):
        """Test get_size returns valid dimensions."""
        term = TerminalManager()
        width, height = term.get_size()
        self.assertIsInstance(width, int)
        self.assertIsInstance(height, int)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
    
    @patch('os.get_terminal_size')
    def test_size_detection_fallback(self, mock_get_size):
        """Test fallback when terminal size detection fails."""
        mock_get_size.side_effect = OSError("No terminal")
        term = TerminalManager()
        width, height = term.get_size()
        self.assertEqual(width, 80)
        self.assertEqual(height, 24)
    
    def test_tmux_detection(self):
        """Test TMUX environment detection."""
        # Without TMUX
        if 'TMUX' in os.environ:
            del os.environ['TMUX']
        term = TerminalManager()
        self.assertFalse(term.is_tmux())
        
        # With TMUX
        os.environ['TMUX'] = '/tmp/tmux-501/default,1234,0'
        term2 = TerminalManager()
        self.assertTrue(term2.is_tmux())
        
        # Cleanup
        if 'TMUX' in os.environ:
            del os.environ['TMUX']
    
    def test_resize_callback_registration(self):
        """Test resize callback can be registered."""
        term = TerminalManager()
        callback_called = []
        
        def handler(old_size, new_size):
            callback_called.append((old_size, new_size))
        
        term.on_resize(handler)
        self.assertEqual(len(term._resize_handlers), 1)
    
    def test_cursor_operations(self):
        """Test cursor manipulation methods don't crash."""
        term = TerminalManager()
        # These should not raise exceptions
        term.save_cursor()
        term.hide_cursor()
        term.show_cursor()
        term.restore_cursor()
    
    def test_clear_screen(self):
        """Test clear_screen doesn't crash."""
        term = TerminalManager()
        term.clear_screen()  # Should not raise
    
    def test_move_cursor(self):
        """Test cursor movement."""
        term = TerminalManager()
        term.move_cursor(1, 1)  # Should not raise
        term.move_cursor(10, 20)  # Should not raise


if __name__ == '__main__':
    unittest.main()
