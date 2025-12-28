import sys
import time
import math
import shutil
import random

# --- COLORS (ANSI 256) ---
C_RESET  = "\033[0m"
C_BLUE   = "\033[38;5;33m"   # Deep Blue/Cyan for the solid body
C_ORANGE = "\033[38;5;208m"  # Bright Orange for the top line
C_BAR_BG = "\033[48;5;235m"  # Dark background for progress bar
C_BAR_FG = "\033[38;5;45m"   # Cyan foreground for progress bar stripes

# --- BRAILLE LUT (5x5) ---
# Maps (StartHeight, EndHeight) -> Unicode Char
# Resolution: 0=Empty, 1=1/4, 2=1/2, 3=3/4, 4=Full
LUT = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

def generate_demo_data(length):
    """
    Generates data that mimics your screenshot:
    - Noisy waves
    - A massive 'Burj Khalifa' spike
    - Distributed network noise
    """
    data = []
    for x in range(length):
        # Base wave
        val = 10 + math.sin(x * 0.1) * 5
        
        # Add 'Distributed Network' noise
        val += random.uniform(-2, 2)
        
        # The 'Burj Khalifa' Spike (at 30% mark)
        if length * 0.3 < x < length * 0.35:
             # Exponential spike
             dist = abs(x - length * 0.325)
             val += 80 * math.exp(-dist * 0.5)
        
        # Secondary hills
        if x > length * 0.6:
            val += 15 * math.sin((x - length*0.6) * 0.2) * math.exp(-(x-length*0.6)*0.01)

        data.append(max(0, val))
    return data

def render_frame(data, visible_count, width, height):
    """
    Renders the chart up to 'visible_count' index.
    """
    output = []
    
    # 1. Normalize Data (Fit to Height)
    # We fix the max scale to the dataset's max to keep the graph stable during animation
    global_max = max(data) if data else 1
    if global_max == 0: global_max = 1
    scale_y = (height * 4) / global_max
    
    # Only process points up to visible_count
    # We pad the rest with 0 for the "Reveal" effect
    active_data = data[:visible_count]
    normalized = [(v * scale_y) for v in active_data]
    
    # Pad the rest of the width with empty space/zeros so the graph frame is stable
    padding = [0] * (width - len(normalized))
    full_view = normalized + padding
    
    # 2. Render Rows (Top to Bottom)
    for r in range(height - 1, -1, -1):
        row_str = ""
        row_bottom = r * 4
        row_top = (r + 1) * 4
        
        for i in range(len(full_view) - 1):
            # Current and Next point (to determine slope)
            y1 = full_view[i]
            y2 = full_view[i+1]
            
            # Optimization: If we are past the visible cursor, print empty
            if i >= visible_count:
                row_str += " "
                continue

            # LOGIC:
            # If the segment passes through this row -> ORANGE LINE
            # If the segment is fully above this row -> BLUE BODY
            # If the segment is fully below this row -> EMPTY
            
            if y1 >= row_top and y2 >= row_top:
                # Fully filled body
                row_str += f"{C_BLUE}⣿"
            elif y1 < row_bottom and y2 < row_bottom:
                # Empty air
                row_str += " "
            else:
                # THE EDGE CASE (Line passes through)
                # Calculate relative heights (0-4)
                ly1 = int(max(0, min(4, y1 - row_bottom)))
                ly2 = int(max(0, min(4, y2 - row_bottom)))
                
                # Look up the specific slope character
                char = LUT[ly1][ly2]
                
                # This is the "Orange Dotted Line" on top
                row_str += f"{C_ORANGE}{char}"
        
        output.append(row_str + C_RESET)
    
    # 3. Render Synced Progress Bar
    # Calculate fill ratio based on visible_count
    progress = visible_count / len(data)
    bar_filled = int(width * progress)
    
    # Create the striped bar pattern /////
    pattern = "////"
    filled_part = (pattern * (bar_filled // 4 + 1))[:bar_filled]
    empty_part = " " * (width - bar_filled)
    
    bar_line = f"{C_BAR_BG}{C_BAR_FG}{filled_part}{C_RESET}{C_BAR_BG}{empty_part}{C_RESET}"
    output.append(bar_line)
    
    return "\n".join(output)

def main():
    # Setup
    try:
        TERM_W, TERM_H = shutil.get_terminal_size()
    except:
        TERM_W, TERM_H = 80, 24
        
    CHART_H = 12
    # Reserve width for margins
    CHART_W = TERM_W - 2
    
    # Generate the full dataset (Scale to terminal width)
    # We want the animation to take about 5-8 seconds
    # So we'll make the dataset exactly the width of the screen, 
    # and reveal 1 column per tick.
    full_data = generate_demo_data(CHART_W)
    
    # Hide Cursor
    sys.stdout.write("\033[?25l")
    
    try:
        # ANIMATION LOOP
        # We iterate from 1 to CHART_W to "reveal" the graph
        for i in range(1, CHART_W + 1):
            
            frame = render_frame(full_data, i, CHART_W, CHART_H)
            
            sys.stdout.write(frame)
            sys.stdout.flush()
            
            # Move cursor back up to overwrite next frame
            # We printed CHART_H lines + 1 Progress bar line
            sys.stdout.write(f"\r\033[{CHART_H + 1}A")
            
            # Speed of animation
            time.sleep(0.04)
            
    except KeyboardInterrupt:
        pass
    finally:
        # Move down and show cursor
        sys.stdout.write(f"\033[{CHART_H + 2}B")
        sys.stdout.write("\033[?25h")

if __name__ == "__main__":
    main()
