import sys
import time
import math
import shutil
import random

# --- CONFIGURATION ---
# Colors (ANSI 256)
C_RESET = "\033[0m"
C_YELLOW = "\033[38;5;220m" # Bright Yellow for the "Glow" line
C_CYAN   = "\033[38;5;33m"  # Blue/Cyan for the "Fill"
C_GRAY   = "\033[38;5;236m" # Dark Gray for empty background (optional)
C_BAR_BG = "\033[48;5;236m" # Background of progress bar
C_BAR_FG = "\033[38;5;45m"  # Foreground (Stripes) of progress bar

# 5x5 LUT (The logic we built previously)
LUT = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

def render_frame(data_window, total_progress, width, height):
    """
    data_window: The slice of data currently visible
    total_progress: Float 0.0 to 1.0
    """
    output = []
    
    # 1. Scaling
    # We fix the scale based on expected data max (e.g. 100) to keep graph stable
    # Or dynamic: mn, mx = min(data_window), max(data_window)
    mx = 100.0 
    mn = 0.0
    scale_y = (height * 4) / (mx - mn)
    norm_data = [(x - mn) * scale_y for x in data_window]
    
    # 2. Render Graph Rows (Top to Bottom)
    for r in range(height - 1, -1, -1):
        line_buffer = ""
        row_bottom = r * 4
        row_top = (r + 1) * 4
        
        for i in range(len(norm_data) - 1):
            y1 = norm_data[i]
            y2 = norm_data[i+1]
            
            # Logic: Determine WHICH character to draw
            char = " "
            color = C_RESET
            
            if y1 < row_bottom and y2 < row_bottom:
                # Empty Space (Above the line)
                char = " " 
            elif y1 >= row_top and y2 >= row_top:
                # Fully Filled (Below the line)
                char = "⣿"
                color = C_CYAN # The "Body"
            else:
                # The "Edge" (The Yellow Line)
                ly1 = int(max(0, min(4, y1 - row_bottom)))
                ly2 = int(max(0, min(4, y2 - row_bottom)))
                char = LUT[ly1][ly2]
                color = C_YELLOW # The "Glow"
            
            line_buffer += f"{color}{char}"
        
        output.append(line_buffer + C_RESET)
    
    # 3. Render Progress Bar (The Blue/Cyan strip)
    # We want a striped effect like the image: //////////
    bar_width = width
    filled_len = int(bar_width * total_progress)
    
    bar_str = ""
    # Create the "filled" portion with striped pattern
    fill_pattern = "////" 
    filled_chars = (fill_pattern * (filled_len // 4 + 1))[:filled_len]
    
    bar_str += f"{C_BAR_FG}{C_BAR_BG}{filled_chars}"
    
    # Empty portion
    bar_str += f"\033[48;5;234m" + (" " * (bar_width - filled_len))
    
    output.append(bar_str + C_RESET)
    
    return "\n".join(output)

def main():
    # Setup Data Stream (Simulated "Big" Dataset)
    # 1000 points of a sine wave with noise spikes
    total_points = 1000
    full_data = []
    for i in range(total_points):
        base = (math.sin(i * 0.1) + 1) * 30 + 10 # Base sine wave
        noise = random.random() * 15             # Jitter
        spike = 0
        if i % 50 == 0: spike = 40               # Occasional spike like in image
        full_data.append(base + noise + spike)

    # Setup Terminal
    try:
        cols, rows = shutil.get_terminal_size()
    except:
        cols, rows = 80, 24

    CHART_H = 12
    CHART_W = cols - 2
    
    sys.stdout.write("\033[?25l") # Hide Cursor

    try:
        # Playback Loop
        for i in range(total_points - CHART_W):
            # Sliding Window: Get the next slice of data
            window = full_data[i : i + CHART_W + 1]
            
            # Calculate Progress
            progress = i / (total_points - CHART_W)
            
            # Render
            frame = render_frame(window, progress, CHART_W, CHART_H)
            
            sys.stdout.write(frame)
            sys.stdout.flush()
            
            # Move Cursor Up (Reset for next frame)
            # Height + 1 for the progress bar
            sys.stdout.write(f"\r\033[{CHART_H + 1}A")
            
            time.sleep(0.05) # Animation speed
            
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(f"\033[{CHART_H + 2}B") # Move down safely
        sys.stdout.write("\033[?25h") # Show Cursor

if __name__ == "__main__":
    main()
