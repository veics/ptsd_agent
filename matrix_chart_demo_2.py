import sys
import time
import math
import shutil
import random

# --- CONFIGURATION & COLORS ---
C_ORANGE_EDGE = '\033[38;5;214m'  # Bright Orange (Smooth Edge)
C_GREEN_DOTS  = '\033[38;5;46m'   # Bright Green (The Dotted Line)
C_RESET       = '\033[0m'

# Operation Colors (Matrix Fill)
OP_COLORS = [
    '\033[38;5;110m',  # Blue
    '\033[38;5;108m',  # Green
    '\033[38;5;180m',  # Yellow
    '\033[38;5;174m',  # Red
    '\033[38;5;109m',  # Cyan
]

# Timeline Colors
C_TL_PROGRESS = '\033[38;5;108m'
C_TL_CURSOR   = '\033[38;5;65m'
C_TL_EMPTY    = '\033[38;5;240m'

# --- 1. SMOOTH EDGE LUT (For Orange Line) ---
# Maps slope start/end to a connected line shape
LUT_EDGE = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

# --- 2. DOT MAPPER (For Green Line) ---
# Maps exact vertical height (0.0-4.0) to a SINGLE dot.
# We use dots from the right column of the Braille cell (dots 4,5,6,8)
# to create a consistent, aligned "bead" effect.
def get_dot_char(local_height):
    # local_height is relative to the bottom of the character (0.0 to 4.0)
    if local_height >= 3.0: return '⠈' # Top dot
    if local_height >= 2.0: return '⠐' # Mid-High dot
    if local_height >= 1.0: return '⠠' # Mid-Low dot
    return '⢀'                       # Bottom dot

def generate_main_data(length):
    """Generates the main filled volume (Solid Chart)."""
    data = []
    for x in range(length):
        # Base Curve: A few nice hills
        val = 10 + math.sin(x * 0.1) * 8
        val += math.sin(x * 0.3) * 3
        
        # Add a "Plateau" or "Spike"
        if x % 80 in range(40, 55): val += 6
        
        data.append(max(1, val))
    return data

def generate_green_data(length, main_data):
    """Generates the green dotted line."""
    data = []
    for i in range(length):
        # It roughly follows the main data but 'floats' independently
        base = main_data[i]
        
        # Add a smooth sine wave offset to make it weave
        # This shows off the overlay effect clearly
        offset = 4 + math.sin(i * 0.2) * 3.5
        
        data.append(base + offset)
    return data

def render_frame(data_main, data_green, visible_idx, width, height):
    output = []
    
    # 1. Scale Data
    # Get global max to keep scale steady
    max_val = max(max(data_main), max(data_green)) if data_main else 1
    # Add small buffer (+2) so the top green dots don't clip
    scale_y = (height * 4) / (max_val + 2)
    
    norm_main = [(v * scale_y) for v in data_main[:visible_idx]]
    norm_green = [(v * scale_y) for v in data_green[:visible_idx]]
    
    # 2. Render Rows (Top to Bottom)
    for r in range(height - 1, -1, -1):
        line_buffer = ""
        row_bottom = r * 4
        row_top = (r + 1) * 4
        
        for i in range(width):
            if i >= len(norm_main) - 1:
                line_buffer += " "
                continue

            # --- LAYER 1: Main Chart (Solid + Orange Edge) ---
            m_y1, m_y2 = norm_main[i], norm_main[i+1]
            
            char_final = " "
            color_final = C_RESET
            
            # Check if this cell is fully inside the main volume
            if m_y1 >= row_top and m_y2 >= row_top:
                char_final = "⣿"
                color_final = random.choice(OP_COLORS)
            # Check if this cell is fully empty (sky)
            elif m_y1 < row_bottom and m_y2 < row_bottom:
                char_final = " "
            # Must be the edge
            else:
                ly1 = int(max(0, min(4, m_y1 - row_bottom)))
                ly2 = int(max(0, min(4, m_y2 - row_bottom)))
                char_final = LUT_EDGE[ly1][ly2]
                color_final = C_ORANGE_EDGE

            # --- LAYER 2: Green Dotted Overlay ---
            # We calculate the exact single dot for the green line at this column
            g_y = norm_green[i]
            
            # Check if the green dot falls inside this specific row
            if row_bottom <= g_y < row_top:
                # Calculate local height (0.0 to 3.99)
                local_h = g_y - row_bottom
                
                # Get the specific dot character
                dot_char = get_dot_char(local_h)
                
                # OVERLAY: The dot replaces whatever is behind it
                char_final = dot_char
                color_final = C_GREEN_DOTS

            line_buffer += f"{color_final}{char_final}"
        
        output.append(line_buffer + C_RESET)
    
    # 3. Render Timeline
    progress = C_TL_PROGRESS + ("━" * (visible_idx - 1))
    cursor = C_TL_CURSOR + "█"
    empty = C_TL_EMPTY + ("┄" * (width - visible_idx))
    output.append(progress + cursor + empty + C_RESET)
    
    return "\n".join(output)

def main():
    try:
        cols, rows = shutil.get_terminal_size()
    except:
        cols, rows = 80, 24
        
    CHART_ROWS = 5
    WIDTH = cols - 1
    
    # Generate Data
    full_data = generate_main_data(WIDTH)
    green_data = generate_green_data(WIDTH, full_data)
    
    sys.stdout.write("\033[?25l") # Hide Cursor
    
    try:
        for i in range(1, WIDTH):
            frame = render_frame(full_data, green_data, i, WIDTH, CHART_ROWS)
            sys.stdout.write(frame)
            sys.stdout.flush()
            
            # Move cursor back up (Rows + Timeline)
            sys.stdout.write(f"\r\033[{CHART_ROWS + 1}A")
            
            time.sleep(0.04) # 25 FPS
            
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(f"\033[{CHART_ROWS + 1}B\033[?25h\n")

if __name__ == "__main__":
    main()
