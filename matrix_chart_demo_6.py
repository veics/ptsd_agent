# -*- coding: utf-8 -*-
import sys
import time
import math
import shutil
import random

# --- CONFIGURATION & COLORS ---
# Top Line
C_ORANGE_EDGE = '\033[38;5;214m'

# The "Green Light" Chain Line
C_GREEN_CHAIN = '\033[38;5;46m' 

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

# --- 1. REPAIRED BRAILLE LUT (5x5) ---
# Replaced the mojibake (‚†Ä...) with correct Unicode Braille
# Maps slope (start_y, end_y) to a high-res braille character
LUT = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

# --- 2. CHAIN LINK LUT (Green Line) ---
# Creates the "beaded wire" texture (e.g. ⠊ ⠑ ⠒)
LUT_CHAIN = [
    ['⠤', '⠤', '⠔', '⠴', '⠴'], 
    ['⠤', '⠒', '⠊', '⠴', '⠴'], 
    ['⠑', '⠑', '⠒', '⠊', '⠊'], 
    ['⠱', '⠱', '⠑', '⠒', '⠊'], 
    ['⠱', '⠱', '⠱', '⠑', '⠉']  
]

def generate_data(length):
    """Generates the main volume data."""
    data = []
    for x in range(length):
        val = 10 + math.sin(x * 0.15) * 8
        val += random.uniform(-3, 3)
        if x % 40 in [20, 21, 22]:
            val += 15
        data.append(max(1, val))
    return data

def generate_green_data(length, main_data):
    """Generates the green chain line floating above."""
    data = []
    for i in range(length):
        base = main_data[i]
        # Offset slightly above main chart
        offset = 5 + math.sin(i * 0.2) * 3
        data.append(base + offset)
    return data

def render_frame(data, data_green, visible_idx, width, height):
    output = []
    
    # 1. Normalize Data
    max_val = max(max(data), max(data_green)) if data else 1
    # Add buffer (+2) so the green line doesn't clip
    scale_y = (height * 4) / (max_val + 2)
    
    # Slice visible data
    norm_main = [(v * scale_y) for v in data[:visible_idx]]
    norm_green = [(v * scale_y) for v in data_green[:visible_idx]]
    
    # 2. Render Graph Rows (Top to Bottom)
    for r in range(height - 1, -1, -1):
        line_buffer = ""
        row_bottom = r * 4
        row_top = (r + 1) * 4
        
        for i in range(width):
            if i >= len(norm_main) - 1:
                line_buffer += " "
                continue

            # --- LAYER 1: Main Chart (Solid + Edge) ---
            m_y1, m_y2 = norm_main[i], norm_main[i+1]
            
            char_final = " "
            color_final = C_RESET
            
            if m_y1 >= row_top and m_y2 >= row_top:
                # FULL BLOCK (Replaced ‚£ø with ⣿)
                color_final = random.choice(OP_COLORS)
                char_final = "⣿"
            
            elif m_y1 < row_bottom and m_y2 < row_bottom:
                # EMPTY
                char_final = " "
            
            else:
                # EDGE (Smooth Orange Curve)
                ly1 = int(max(0, min(4, m_y1 - row_bottom)))
                ly2 = int(max(0, min(4, m_y2 - row_bottom)))
                char_final = LUT[ly1][ly2]
                color_final = C_ORANGE_EDGE

            # --- LAYER 2: Green Chain Overlay ---
            # If the green line passes through this cell, draw it on top
            g_y1, g_y2 = norm_green[i], norm_green[i+1]
            seg_min, seg_max = min(g_y1, g_y2), max(g_y1, g_y2)
            
            if seg_max > row_bottom and seg_min < row_top:
                gy1_loc = int(max(0, min(4, g_y1 - row_bottom)))
                gy2_loc = int(max(0, min(4, g_y2 - row_bottom)))
                
                chain_char = LUT_CHAIN[gy1_loc][gy2_loc]
                
                # Only overwrite if it's a valid chain link
                if chain_char != '⠀':
                    char_final = chain_char
                    color_final = C_GREEN_CHAIN

            line_buffer += f"{color_final}{char_final}"
        
        output.append(line_buffer + C_RESET)
    
    # 3. Render Timeline (Fixed Characters)
    # Replaced Mojibake with Box Drawing chars
    progress_char = "━" 
    empty_char = "─"
    cursor_char = "█"
    
    tl_line = C_TL_PROGRESS + (progress_char * (visible_idx - 1))
    tl_line += C_TL_CURSOR + cursor_char
    remaining = width - visible_idx
    tl_line += C_TL_EMPTY + (empty_char * remaining)
    
    output.append(tl_line + C_RESET)
    
    return "\n".join(output)

def main():
    try:
        cols, rows = shutil.get_terminal_size()
    except:
        cols, rows = 80, 24
        
    CHART_ROWS = 6 # Height of the chart
    WIDTH = cols - 1 
    
    # Generate datasets
    full_data = generate_data(WIDTH)
    green_data = generate_green_data(WIDTH, full_data)
    
    # Hide Cursor
    sys.stdout.write("\033[?25l")
    
    try:
        # Animation Loop
        for i in range(1, WIDTH):
            frame = render_frame(full_data, green_data, i, WIDTH, CHART_ROWS)
            
            sys.stdout.write(frame)
            sys.stdout.flush()
            
            # Reset Cursor Position (Height + Timeline line)
            sys.stdout.write(f"\r\033[{CHART_ROWS + 1}A")
            
            time.sleep(0.03)
            
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        sys.stdout.write(f"\033[{CHART_ROWS + 1}B")
        sys.stdout.write("\033[?25h")
        print()

if __name__ == "__main__":
    main()
