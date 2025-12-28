"""Shared UI theme with colors and utilities."""

# ANSI Color Codes
RESET = "\033[0m"
DIM = "\033[2m"
GRAY = "\033[90m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
ORANGE = "\033[38;5;208m"

# Washed (dimmed) colors
RED_WASHED = "\033[38;5;167m"
GREEN_WASHED = "\033[38;5;114m"
YELLOW_WASHED = "\033[38;5;185m"
ORANGE_WASHED = "\033[38;5;179m"
CYAN_WASHED = "\033[38;5;117m"
BLUE_WASHED = "\033[38;5;111m"
PINK_LIGHT = "\033[38;5;218m"
RED_BRIGHT = "\033[38;5;196m"
PINK_LIGHT_WASHED = "\033[38;5;182m"
RED_BRIGHT_WASHED = "\033[38;5;160m"

# Tree/UI symbols
TRIANGLE_EXPANDED = "▼"
TRIANGLE_COLLAPSED = "▶"


def get_color_for_value(metric_type: str, value: float) -> str:
    """Get color for a metric value based on thresholds."""
    if metric_type == "coverage":
        if value >= 80:
            return GREEN
        elif value >= 50:
            return YELLOW
        else:
            return GRAY
    elif metric_type == "pass_rate":
        if value >= 95:
            return GREEN
        elif value >= 80:
            return YELLOW
        else:
            return RED
    elif metric_type in ["warnings", "failures", "errors"]:
        if value == 0:
            return GREEN
        elif value < 10:
            return YELLOW
        else:
            return ORANGE
    return GRAY


def get_washed_color_for_value(metric_type: str, value: float) -> str:
    """Get washed (dimmed) color for a metric value."""
    if metric_type == "coverage":
        if value >= 80:
            return GREEN_WASHED
        elif value >= 50:
            return YELLOW_WASHED
        else:
            return GRAY
    elif metric_type == "pass_rate":
        if value >= 95:
            return GREEN_WASHED
        elif value >= 80:
            return YELLOW_WASHED
        else:
            return RED_WASHED
    elif metric_type in ["warnings", "failures", "errors"]:
        if value == 0:
            return GREEN_WASHED
        elif value < 10:
            return YELLOW_WASHED
        else:
            return ORANGE_WASHED
    return GRAY


def get_status_color_name(status: str) -> str:
    """Get color constant name for a status string."""
    status_lower = status.lower()
    if "complete" in status_lower or "done" in status_lower:
        return "GREEN"
    elif "progress" in status_lower or "active" in status_lower:
        return "YELLOW"
    elif "error" in status_lower or "fail" in status_lower:
        return "RED"
    else:
        return "GRAY"


def get_color(color_name: str) -> str:
    """Get ANSI color code by name."""
    colors = {
        "RED": RED,
        "GREEN": GREEN,
        "YELLOW": YELLOW,
        "BLUE": BLUE,
        "CYAN": CYAN,
        "ORANGE": ORANGE,
        "GRAY": GRAY,
        "DIM": DIM,
        "RESET": RESET
    }
    return colors.get(color_name.upper(), RESET)


def get_progress_bar_config():
    """Get progress bar configuration with colors."""
    return {
        "active_color": CYAN,
        "inactive_color": GRAY,
        "blinking_color": ORANGE,
        "reset": RESET
    }
