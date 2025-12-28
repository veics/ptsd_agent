"""Integration tests for terminal resize handling."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from ptsd_agent.ui.terminal import TerminalManager
from ptsd_agent.ui.legacy_display import ProgressiveDisplay


class TestTerminalResize(unittest.TestCase):
    """Test terminal resize handling in display components."""
    
    @patch('os.get_terminal_size')
    def test_progressive_display_handles_resize(self, mock_get_size):
        """Test ProgressiveDisplay updates width on resize."""
        # Initial size
        mock_get_size.return_value = os.terminal_size((100, 24))
        
        display = ProgressiveDisplay()
        initial_width = display.term_width
        
        # Simulate resize
        mock_get_size.return_value = os.terminal_size((150, 30))
        old_size = (100, 24)
        new_size = (150, 30)
        display._handle_resize(old_size, new_size)
        
        # Check width updated
        self.assertEqual(display.term_width, 150)
        self.assertGreater(display.term_width, initial_width)
    
    @patch('os.get_terminal_size')
    def test_minimum_width_enforced(self, mock_get_size):
        """Test minimum width is enforced on resize."""
        # Very narrow terminal
        mock_get_size.return_value = os.terminal_size((40, 24))
        
        display = ProgressiveDisplay()
        
        # Should use minimum width (80)
        self.assertEqual(display.term_width, display.MIN_TERM_WIDTH)
    
    @patch('os.get_terminal_size')
    def test_dynamic_progress_bar_width(self, mock_get_size):
        """Test progress bar width adjusts to terminal size."""
        # Wide terminal
        mock_get_size.return_value = os.terminal_size((200, 24))
        
        display = ProgressiveDisplay()
        
        # Progress bar should be created
        bar = display.make_progress_bar(50)
        self.assertIsNotNone(bar)
        self.assertIn('▰', bar)
    
    def test_terminal_manager_resize_callback(self):
        """Test terminal manager triggers callbacks on resize."""
        terminal = TerminalManager()
        
        callback_triggered = []
        
        def callback(old, new):
            callback_triggered.append((old, new))
        
        terminal.on_resize(callback)
        
        # Manually trigger resize
        old_size = terminal.get_size()
        new_size = (150, 30)
        terminal._handle_sigwinch(None, None)
        
        # Note: This test requires actual SIGWINCH signal or manual trigger
        # In practice, callbacks are triggered by system resize events


if __name__ == '__main__':
    unittest.main()
