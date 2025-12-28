import sys
import time
import math
import shutil
import random

# --- COLORS ---
C_ORANGE_EDGE = '\033[38;5;214m'  # Bright Orange
C_GREEN_CHAIN = '\033[38;5;46m'   # Bright Green (The Chain Line)
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
# Standard smooth curves for the main body
LUT_SMOOTH = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

# --- 2. CHAIN LINK LUT (For Green Line) ---
# This LUT uses specific 2-dot characters to create the "⠊⠑⠒" texture.
# It connects the Left Height to the Right Height with a visual "Link".
# Rows 0-4 represent height within the cell.

LUT_CHAIN = [
    # Right: 0     1     2     3     4
    # Left 0 (Bottom)
    ['⠀', '⢀', '⠠', '⠐', '⠈'], 
    # Left 1 (Low)
    ['⡀', '⣀', '⠔', '⠢', '⠑'], 
    # Left 2 (Mid) - The "⠒" zone
    ['⠠', '⠔', '⠤', '⠒', '⠊'], 
    # Left 3 (High)
    ['⠐', '⠡', '⠒', '⠒', '⠊'], 
    # Left 4 (Top)
    ['⠈', '⠑', '⠑', '⠉', '⠉']
]

def generate_main_data(length):
    """Generates the main volume."""
    data = []
    for x in range(length):
        # Base Curve
        val = 12 + math.sin(x * 0.1) * 8
        val += math.sin(x * 0.3) * 4
        # Plateaus
        if x % 100 in range(10, 30): val = 18 + random.uniform(-0.5, 0.5)
        # Spikes
        if x % 50 == 0: val += 12
        
        data.append(max(1, val))
    return data

def generate_green_data(length, main_data):
    """Generates the green chain line."""
    data = []
    for i in range(length):
        base = main_data[i]
        # Offset slightly above main chart
        offset = 5 + math.sin(i * 0.2) * 3
        # No random jitter needed, the LUT texture provides the scatter look
        data.append(base + offset)
    return data

def render_frame(data_main, data_green, visible_idx, width, height):
    output = []
    
    # 1. Scale Data
    max_val = max(max(data_main), max(data_green)) if data_main else 1
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

            # --- LAYER 1: Main Chart ---
            m_y1, m_y2 = norm_main[i], norm_main[i+1]
            
            char_final = " "
            color_final = C_RESET
            
            if m_y1 >= row_top and m_y2 >= row_top:
                char_final = "⣿"
                color_final = random.choice(OP_COLORS)
            elif m_y1 < row_bottom and m_y2 < row_bottom:
                char_final = " "
            else:
                ly1 = int(max(0, min(4, m_y1 - row_bottom)))
                ly2 = int(max(0, min(4, m_y2 - row_bottom)))
                char_final = LUT_SMOOTH[ly1][ly2]
                color_final = C_ORANGE_EDGE

            # --- LAYER 2: Green Chain Line ---
            g_y1, g_y2 = norm_green[i], norm_green[i+1]
            
            # Logic: If the green line segment passes through this cell
            seg_min, seg_max = min(g_y1, g_y2), max(g_y1, g_y2)
            
            if seg_max > row_bottom and seg_min < row_top:
                # Map entrance/exit heights to 0-4 range
                gy1_loc = int(max(0, min(4, g_y1 - row_bottom)))
                gy2_loc = int(max(0, min(4, g_y2 - row_bottom)))
                
                # Look up the specific chain character (⠊, ⠑, ⠒, etc.)
                chain_char = LUT_CHAIN[gy1_loc][gy2_loc]
                
                # Only draw if it's not empty (avoids wiping background unnecessarily)
                if chain_char != '⠀':
                    char_final = chain_char
                    color_final = C_GREEN_CHAIN

            line_buffer += f"{color_final}{char_final}"
        
        output.append(line_buffer + C_RESET)
    
    # 3. Timeline
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
        
    CHART_ROWS = 6
    WIDTH = cols - 1
    
    full_data = generate_main_data(WIDTH)
    green_data = generate_green_data(WIDTH, full_data)
    
    sys.stdout.write("\033[?25l") # Hide Cursor
    
    try:
        for i in range(1, WIDTH):
            frame = render_frame(full_data, green_data, i, WIDTH, CHART_ROWS)
            sys.stdout.write(frame)
            sys.stdout.flush()
            sys.stdout.write(f"\r\033[{CHART_ROWS + 1}A")
            time.sleep(0.04)
            
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(f"\033[{CHART_ROWS + 1}B\033[?25h\n")

if __name__ == "__main__":
    main()
