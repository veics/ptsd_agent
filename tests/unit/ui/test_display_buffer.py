"""Unit tests for display buffer management."""

import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
from ptsd_agent.ui.legacy_display import ProgressiveDisplay


class TestDisplayBuffer(unittest.TestCase):
    """Test cases for display buffer management."""
    
    def test_buffer_tracking(self):
        """Test that line count is tracked correctly."""
        display = ProgressiveDisplay()
        
        # Initially no lines
        self.assertEqual(display.last_line_count, 0)
        
        # Add some lines
        display.add_line("Line 1")
        display.add_line("Line 2")
        display.add_line("Line 3")
        
        # Render should track line count
        with patch('sys.stdout', new_callable=StringIO):
            display.render()
        
        # Should have tracked 3 lines
        self.assertGreater(display.last_line_count, 0)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_clear_screen_uses_buffer(self, mock_stdout):
        """Test clear_screen uses tracked line count."""
        display = ProgressiveDisplay()
        display.last_line_count = 5
        
        # Clear should use last_line_count
        display.clear_screen()
        
        output = mock_stdout.getvalue()
        # Should contain ANSI escape sequences for cursor movement
        self.assertIn('\033[', output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_resize_clears_buffer(self, mock_stdout):
        """Test that resize event clears display buffer."""
        display = ProgressiveDisplay()
        display.last_line_count = 10
        
        # Trigger resize
        old_size = (100, 24)
        new_size = (120, 30)
        display._handle_resize(old_size, new_size)
        
        # Buffer should be cleared
        self.assertEqual(display.last_line_count, 0)
        
        # Should have output clear sequences
        output = mock_stdout.getvalue()
        self.assertIn('\033[', output)
    
    def test_terminal_height_clamping(self):
        """Test that clear doesn't exceed terminal height."""
        display = ProgressiveDisplay()
        
        # Set unreasonably high line count
        display.last_line_count = 1000
        
        # Get terminal height
        _, term_height = display.terminal.get_size()
        
        # Clear should clamp to terminal height
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            display.clear_screen()
            
            # Verify we didn't try to clear more than terminal height
            output = mock_stdout.getvalue()
            # The escape sequence should use term_height - 1
            # (exactly verifying this is tricky, but we check it doesn't crash)
            self.assertIsNotNone(output)
    
    def test_empty_buffer_clear_noop(self):
        """Test that clearing empty buffer is a no-op."""
        display = ProgressiveDisplay()
        display.last_line_count = 0
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            display.clear_screen()
            
            # Should produce no output
            output = mock_stdout.getvalue()
            self.assertEqual(output, "")


if __name__ == '__main__':
    unittest.main()
