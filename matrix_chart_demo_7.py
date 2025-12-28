# -*- coding: utf-8 -*-
import sys
import time
import math
import shutil
import random

# --- CONFIGURATION & COLORS ---
C_ORANGE_EDGE = '\033[38;5;214m'  # Orange Top Line
C_GREEN_CHAIN = '\033[38;5;46m'   # Bright Green Beaded Line
C_RESET       = '\033[0m'

# Operation Colors
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

# --- 1. SMOOTH EDGE LUT (Standard Braille) ---
LUT_SMOOTH = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

# --- 2. CHAIN LINK LUT (The Beaded Green Line) ---
# Designed to look like a connected wire (⠒ ⠴ ⠑)
LUT_CHAIN = [
    ['⠤', '⠤', '⠔', '⠴', '⠴'], 
    ['⠤', '⠒', '⠊', '⠴', '⠴'], 
    ['⠑', '⠑', '⠒', '⠊', '⠊'], 
    ['⠱', '⠱', '⠑', '⠒', '⠊'], 
    ['⠱', '⠱', '⠱', '⠑', '⠉']  
]

CHAR_FILL = '⣿'

def generate_main_data(length):
    """Generates the main volume data."""
    data = []
    for x in range(length):
        val = 10 + math.sin(x * 0.15) * 8
        val += random.uniform(-2, 2)
        if x % 45 in [20, 21, 22]: # Occasional spikes
            val += 12
        data.append(max(1, val))
    return data

def generate_green_data(length, main_data):
    """Generates a SMOOTH green line to prevent gaps."""
    data = []
    # 1. Create raw offset data
    for i in range(length):
        base = main_data[i]
        offset = 5 + math.sin(i * 0.2) * 3
        data.append(base + offset)
    
    # 2. Smooth it out to prevent "cuts" (moving > 4 dots per column)
    # Simple moving average to ensure connectivity
    smoothed = []
    for i in range(length):
        start = max(0, i-2)
        end = min(length, i+2)
        avg = sum(data[start:end]) / (end - start)
        smoothed.append(avg)
        
    return smoothed

def render_frame(data_main, data_green, visible_idx, width, height):
    output = []
    
    # 1. Scale Data
    # Add buffer (+3) to ensure green line never hits the ceiling
    max_val = max(max(data_main), max(data_green)) if data_main else 1
    scale_y = (height * 4) / (max_val + 3)
    
    norm_main = [(v * scale_y) for v in data_main[:visible_idx]]
    norm_green = [(v * scale_y) for v in data_green[:visible_idx]]
    
    # 2. Render Graph Rows
    for r in range(height - 1, -1, -1):
        line_buffer = ""
        row_bottom = r * 4
        row_top = (r + 1) * 4
        
        for i in range(width):
            if i >= len(norm_main) - 1:
                line_buffer += " "
                continue

            # --- LAYER 1: Base Chart ---
            m_y1, m_y2 = norm_main[i], norm_main[i+1]
            
            char_final = " "
            color_final = C_RESET
            
            if m_y1 >= row_top and m_y2 >= row_top:
                color_final = random.choice(OP_COLORS)
                char_final = CHAR_FILL
            elif m_y1 < row_bottom and m_y2 < row_bottom:
                char_final = " "
            else:
                ly1 = int(max(0, min(4, m_y1 - row_bottom)))
                ly2 = int(max(0, min(4, m_y2 - row_bottom)))
                char_final = LUT_SMOOTH[ly1][ly2]
                color_final = C_ORANGE_EDGE

            # --- LAYER 2: Green Chain Overlay ---
            # Strict logic: Only draw if the line actually exists in this row
            g_y1, g_y2 = norm_green[i], norm_green[i+1]
            seg_min, seg_max = min(g_y1, g_y2), max(g_y1, g_y2)
            
            # Check intersection with this row
            if seg_max > row_bottom and seg_min < row_top:
                # Calculate local coordinates (0 to 4)
                gy1_loc = int(max(0, min(4, g_y1 - row_bottom)))
                gy2_loc = int(max(0, min(4, g_y2 - row_bottom)))
                
                chain_char = LUT_CHAIN[gy1_loc][gy2_loc]
                
                if chain_char != '⠀':
                    char_final = chain_char
                    color_final = C_GREEN_CHAIN

            line_buffer += f"{color_final}{char_final}"
        
        output.append(line_buffer + C_RESET)
    
    # 3. Render Timeline
    progress_char = "━" 
    empty_char = "┄"
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
