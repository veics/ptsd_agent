import shutil
import sys

class TerminalManager:
    """Manages terminal state and responsiveness"""
    
    def __init__(self):
        self._set_width()

    def _set_width(self):
        self.width = shutil.get_terminal_size().columns

    def refresh(self):
        self._set_width()

    def clear_line(self):
        """Clear the current line in the terminal"""
        sys.stdout.write("\033[K")
        sys.stdout.flush()

    def move_up(self, n=1):
        """Move cursor up n lines"""
        if n > 0:
            sys.stdout.write(f"\033[{n}F")
            sys.stdout.flush()

    def hide_cursor(self):
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    def show_cursor(self):
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
