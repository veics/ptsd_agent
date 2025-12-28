"""Terminal abstraction layer with resize handling and TMUX support.

This module provides a unified interface for terminal operations including:
- Terminal size detection with fallback
- SIGWINCH signal handling for resize events
- TMUX environment detection
- Cursor manipulation
- Buffer management
"""

import os
import sys
import signal
import threading
import logging
from typing import Tuple, Callable, List, Optional

logger = logging.getLogger(__name__)


class TerminalManager:
    """Manages terminal state, resize events, and provides abstraction layer.
    
    Features:
    - Automatic terminal size detection
    - SIGWINCH signal handling for resize events
    - TMUX environment detection
    - Graceful fallback for non-TTY environments
    - Thread-safe resize event callbacks
    
    Example:
        terminal = TerminalManager()
        terminal.on_resize(lambda old, new: print(f"Resized from {old} to {new}"))
        width, height = terminal.get_size()
    """
    
    def __init__(self):
        """Initialize terminal manager and set up resize handling."""
        self.is_tty = sys.stdout.isatty()
        self._resize_handlers: List[Callable[[Tuple[int, int], Tuple[int, int]], None]] = []
        self._original_sigwinch: Optional[signal.Handlers] = None
        self._lock = threading.Lock()
        
        # Detect initial terminal size
        self.width, self.height = self._detect_size()
        
        # Detect TMUX environment
        self._in_tmux = self._is_tmux()
        
        # Set up resize handler if in TTY and main thread
        if self.is_tty and threading.current_thread() == threading.main_thread():
            self._setup_resize_handler()
            logger.debug(f"Terminal manager initialized: {self.width}x{self.height}, TMUX={self._in_tmux}")
        else:
            if not self.is_tty:
                logger.warning("Non-TTY environment detected, using static terminal size")
            else:
                logger.warning("Not in main thread, resize handling disabled")
    
    def _detect_size(self) -> Tuple[int, int]:
        """Detect current terminal size with fallback.
        
        Returns:
            Tuple of (width, height) in characters
        """
        try:
            size = os.get_terminal_size()
            return (size.columns, size.lines)
        except OSError:
            # Fallback for non-TTY environments (piped output, etc.)
            logger.debug("Could not detect terminal size, using fallback 80x24")
            return (80, 24)
    
    def _is_tmux(self) -> bool:
        """Detect if running in TMUX session.
        
        Returns:
            True if TMUX environment variable is set
        """
        return 'TMUX' in os.environ
    
    def _setup_resize_handler(self):
        """Set up SIGWINCH signal handler for terminal resize events."""
        try:
            # Save original handler
            self._original_sigwinch = signal.signal(signal.SIGWINCH, self._handle_sigwinch)
            logger.debug("SIGWINCH handler registered")
        except (ValueError, OSError) as e:
            # Signal not supported on this platform or not in main thread
            logger.warning(f"Could not register SIGWINCH handler: {e}")
    
    def _handle_sigwinch(self, signum, frame):
        """Handle SIGWINCH signal when terminal is resized.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        with self._lock:
            old_size = (self.width, self.height)
            new_size = self._detect_size()
            
            if old_size != new_size:
                self.width, self.height = new_size
                logger.debug(f"Terminal resized: {old_size} -> {new_size}")
                
                # Notify all registered handlers
                for handler in self._resize_handlers:
                    try:
                        handler(old_size, new_size)
                    except Exception as e:
                        logger.error(f"Error in resize handler: {e}")
    
    def get_size(self) -> Tuple[int, int]:
        """Get current terminal size.
        
        Returns:
            Tuple of (width, height) in characters
        """
        with self._lock:
            return (self.width, self.height)
    
    def on_resize(self, handler: Callable[[Tuple[int, int], Tuple[int, int]], None]) -> None:
        """Register a callback for terminal resize events.
        
        Args:
            handler: Callback function taking (old_size, new_size) tuples
        """
        with self._lock:
            self._resize_handlers.append(handler)
            logger.debug(f"Resize handler registered, total handlers: {len(self._resize_handlers)}")
    
    def clear_screen(self) -> None:
        """Clear the entire screen."""
        if self.is_tty:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
    
    def move_cursor(self, row: int, col: int) -> None:
        """Move cursor to specific position.
        
        Args:
            row: Row number (1-indexed)
            col: Column number (1-indexed)
        """
        if self.is_tty:
            sys.stdout.write(f"\033[{row};{col}H")
            sys.stdout.flush()
    
    def save_cursor(self) -> None:
        """Save current cursor position."""
        if self.is_tty:
            sys.stdout.write("\033[s")
            sys.stdout.flush()
    
    def restore_cursor(self) -> None:
        """Restore cursor to saved position."""
        if self.is_tty:
            sys.stdout.write("\033[u")
            sys.stdout.flush()
    
    def hide_cursor(self) -> None:
        """Hide terminal cursor."""
        if self.is_tty:
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()
    
    def show_cursor(self) -> None:
        """Show terminal cursor."""
        if self.is_tty:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
    
    def is_tmux(self) -> bool:
        """Check if running in TMUX session.
        
        Returns:
            True if in TMUX
        """
        return self._in_tmux
    
    def cleanup(self):
        """Clean up resources and restore original signal handlers."""
        if self._original_sigwinch is not None:
            try:
                signal.signal(signal.SIGWINCH, self._original_sigwinch)
                logger.debug("SIGWINCH handler restored")
            except (ValueError, OSError) as e:
                logger.warning(f"Could not restore SIGWINCH handler: {e}")
        
        # Show cursor on cleanup
        self.show_cursor()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
