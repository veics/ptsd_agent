import sys
import time
import math
import shutil
import random

# --- CONFIGURATION & COLORS ---
# Top Line
C_ORANGE_EDGE = '\033[38;5;214m'

# Operation Colors (Fill Blocks)
OP_COLORS = [
    '\033[38;5;110m',  # Blue (DISCOVERY)
    '\033[38;5;108m',  # Green (EXECUTION)
    '\033[38;5;180m',  # Yellow (AI_ANALYSIS)
    '\033[38;5;174m',  # Red (AUTO_FIX)
    '\033[38;5;109m',  # Cyan (CACHE)
]

# Timeline Colors
C_TL_PROGRESS = '\033[38;5;108m'  # Green
C_TL_CURSOR   = '\033[38;5;65m'   # Faded Green
C_TL_EMPTY    = '\033[38;5;240m'  # Gray
C_RESET       = '\033[0m'

# --- BRAILLE LUT (5x5) ---
# Maps slope (start_y, end_y) to a high-res braille character
LUT = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

def generate_data(length):
    """Generates a noisy wave with peaks to fit a 5-row chart."""
    data = []
    for x in range(length):
        # Sine wave base
        val = 10 + math.sin(x * 0.15) * 8
        # Add noise
        val += random.uniform(-3, 3)
        # Add a big spike every ~40 chars
        if x % 40 in [20, 21, 22]:
            val += 15
        data.append(max(1, val))
    return data

def render_frame(data, visible_idx, width, height):
    """
    Renders one frame of the animation.
    visible_idx: How many columns from the left are currently revealed.
    """
    output = []
    
    # 1. Normalize Data
    # We fix the vertical scale so the graph doesn't "bounce" as it fills
    global_max = max(data) if data else 1
    scale_y = (height * 4) / global_max
    
    # Prepare the visible slice + padding for the rest of the screen
    # This keeps the frame width constant
    visible_data = data[:visible_idx]
    normalized = [(v * scale_y) for v in visible_data]
    
    # 2. Render Graph Rows (Top to Bottom)
    # range(4, -1, -1) creates rows 4, 3, 2, 1, 0
    for r in range(height - 1, -1, -1):
        line_buffer = ""
        row_bottom = r * 4
        row_top = (r + 1) * 4
        
        for i in range(width):
            # If we are in the "future" (empty part of screen), print space
            if i >= len(normalized) - 1:
                line_buffer += " "
                continue

            y1 = normalized[i]
            y2 = normalized[i+1]
            
            # LOGIC: Fill vs Edge vs Empty
            if y1 >= row_top and y2 >= row_top:
                # FULL BLOCK (Inside the volume)
                # Randomly pick an operation color for this specific block
                color = random.choice(OP_COLORS)
                line_buffer += f"{color}⣿"
            
            elif y1 < row_bottom and y2 < row_bottom:
                # EMPTY (Sky)
                line_buffer += " "
            
            else:
                # EDGE (The curve)
                # Calculate sub-block coords (0-4)
                ly1 = int(max(0, min(4, y1 - row_bottom)))
                ly2 = int(max(0, min(4, y2 - row_bottom)))
                char = LUT[ly1][ly2]
                # Use the dedicated Orange Edge Color
                line_buffer += f"{C_ORANGE_EDGE}{char}"
        
        output.append(line_buffer + C_RESET)
    
    # 3. Render Timeline
    # [/////////|................]
    # Green ///, Faded |, Gray ...
    
    progress_char = "━" 
    empty_char = "┄"
    
    # Progress part
    tl_line = C_TL_PROGRESS + (progress_char * (visible_idx - 1))
    
    # Cursor part (Blinking effect logic could go here, for now solid)
    tl_line += C_TL_CURSOR + "█"
    
    # Empty part
    remaining = width - visible_idx
    tl_line += C_TL_EMPTY + (empty_char * remaining)
    
    output.append(tl_line + C_RESET)
    
    return "\n".join(output)

def main():
    # Setup Terminal
    try:
        cols, rows = shutil.get_terminal_size()
    except:
        cols, rows = 80, 24
        
    CHART_ROWS = 5
    # Width margin to prevent line wrapping issues
    WIDTH = cols - 1 
    
    # Generate full dataset
    full_data = generate_data(WIDTH)
    
    # Hide Cursor
    sys.stdout.write("\033[?25l")
    
    try:
        # Animation Loop
        # Iterate 1 to WIDTH to slide the graph in
        for i in range(1, WIDTH):
            frame = render_frame(full_data, i, WIDTH, CHART_ROWS)
            
            sys.stdout.write(frame)
            sys.stdout.flush()
            
            # Reset Cursor Position (Up 5 rows + 1 timeline row = 6)
            sys.stdout.write(f"\r\033[{CHART_ROWS + 1}A")
            
            # Speed control
            time.sleep(0.03)
            
    except KeyboardInterrupt:
        pass
    finally:
        # Move cursor down to bottom and unhide
        sys.stdout.write(f"\033[{CHART_ROWS + 1}B")
        sys.stdout.write("\033[?25h")
        print() # Newline

if __name__ == "__main__":
    main()
