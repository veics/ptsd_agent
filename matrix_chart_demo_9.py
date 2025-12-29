# -*- coding: utf-8 -*-
import sys
import time
import math
import shutil
import random

# --- CONFIGURATION & COLORS ---
C_ORANGE_EDGE = '\033[38;5;214m'  # Orange Top Line
C_GREEN_CHAIN = '\033[38;5;46m'   # Bright Green Beaded Line
C_LABEL       = '\033[38;5;250m'  # White/Grey for Text Labels
C_CYAN_AXIS   = '\033[38;5;81m'   # Cyan for Axes and Progress Done
C_GREY_TODO   = '\033[38;5;236m'  # Dark Grey for Progress ToDo (Thick Line)
C_RESET       = '\033[0m'

# Operation Colors
OP_COLORS = [
    '\033[38;5;110m',  # Blue
    '\033[38;5;108m',  # Green
    '\033[38;5;180m',  # Yellow
    '\033[38;5;174m',  # Red
    '\033[38;5;109m',  # Cyan
]

# --- LUTs ---
LUT_SMOOTH = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

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
        if x % 45 in [20, 21, 22]: val += 12
        data.append(max(1, val))
    return data

def generate_green_data(length, main_data):
    """Generates the smoothed green line."""
    data = []
    # 1. Raw Data
    raw = []
    for i in range(length):
        base = main_data[i]
        offset = 5 + math.sin(i * 0.2) * 3
        raw.append(base + offset)
    
    # 2. Smooth it
    for i in range(length):
        start = max(0, i-2)
        end = min(length, i+2)
        avg = sum(raw[start:end]) / (end - start)
        data.append(avg)
    return data

def render_frame(data_main, data_green, visible_idx, chart_w, chart_h, start_time):
    output = []
    
    # --- Y-AXIS LABELS ---
    y_labels = [" 128", "  64", "  32", "  16", "   8", "   4"]
    
    # 1. Scale Data
    max_val = max(max(data_main), max(data_green)) if data_main else 1
    scale_y = (chart_h * 4) / (max_val + 3)
    
    norm_main = [(v * scale_y) for v in data_main[:visible_idx]]
    norm_green = [(v * scale_y) for v in data_green[:visible_idx]]
    
    # 2. Render Graph Rows
    for r in range(chart_h - 1, -1, -1):
        line_buffer = ""
        
        # Y-AXIS: Thick Cyan Line (┃)
        # 5 chars for label + 1 space + 1 char axis + 1 char padding = 8 chars offset
        if r < len(y_labels):
            label_idx = min(r, len(y_labels)-1)
            line_buffer += f"{C_LABEL}{y_labels[label_idx]} {C_CYAN_AXIS}┃ {C_RESET}"
        else:
            line_buffer += f"     {C_CYAN_AXIS}┃ {C_RESET}"
            
        row_bottom = r * 4
        row_top = (r + 1) * 4
        
        for i in range(chart_w):
            if i >= len(norm_main) - 1:
                line_buffer += " "
                continue

            # LAYER 1: Base Chart
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

            # LAYER 2: Green Chain
            g_y1, g_y2 = norm_green[i], norm_green[i+1]
            seg_min, seg_max = min(g_y1, g_y2), max(g_y1, g_y2)
            
            if seg_max > row_bottom and seg_min < row_top:
                gy1_loc = int(max(0, min(4, g_y1 - row_bottom)))
                gy2_loc = int(max(0, min(4, g_y2 - row_bottom)))
                chain_char = LUT_CHAIN[gy1_loc][gy2_loc]
                if chain_char != '⠀':
                    char_final = chain_char
                    color_final = C_GREEN_CHAIN

            line_buffer += f"{color_final}{char_final}"
        
        output.append(line_buffer + C_RESET)
    
    # 3. Render X-Axis (Thick Pip-Style Bar with Gap)
    # Visual: [Cyan━━━━━ Gap Grey━━━━━]
    
    # We reserve 1 char for the gap, unless bar is 100% full
    filled_len = visible_idx
    if filled_len >= chart_w:
        filled_len = chart_w
        gap_len = 0
        remaining_len = 0
    else:
        gap_len = 1
        # Prevent overflow
        if filled_len > chart_w - 1: filled_len = chart_w - 1
        remaining_len = chart_w - filled_len - gap_len
    
    # Construct Parts
    bar_filled = f"{C_CYAN_AXIS}" + ("━" * filled_len)
    bar_gap    = " " * gap_len
    bar_empty  = f"{C_GREY_TODO}" + ("━" * remaining_len)
    
    # Corner: Heavy Up+Right (┗) + Heavy Horizontal (━)
    corner = f"   0 {C_CYAN_AXIS}┗━" 
    
    axis_line = f"{corner}{bar_filled}{bar_gap}{bar_empty}{C_RESET}"
    output.append(axis_line)
    
    # 4. Render X-Axis Time Labels
    elapsed = time.time() - start_time
    padding = " " * 7 
    
    label_chars = [" "] * chart_w
    
    # A. Start Label
    label_start = "0s"
    for k, ch in enumerate(label_start):
        if k < chart_w: label_chars[k] = ch
        
    # B. Current Time Label (Follows the gap)
    t_str = f"{elapsed:.1f}s"
    pos = filled_len
    # Ensure it doesn't overwrite 0s or fall off edge
    if pos < 2: pos = 2
    
    for k, ch in enumerate(t_str):
        if pos + k < chart_w:
            label_chars[pos + k] = ch
            
    label_line_str = "".join(label_chars)
    output.append(f"{padding}{C_LABEL}{label_line_str}{C_RESET}")
    
    return "\n".join(output)

def main():
    try:
        cols, rows = shutil.get_terminal_size()
    except:
        cols, rows = 80, 24
        
    CHART_H = 6
    # 8 chars reserved for Y-axis labels and padding
    CHART_W = cols - 8 
    
    full_data = generate_main_data(CHART_W)
    green_data = generate_green_data(CHART_W, full_data)
    
    sys.stdout.write("\033[?25l") # Hide Cursor
    start_time = time.time()
    
    try:
        # Loop
        for i in range(1, CHART_W + 1):
            frame = render_frame(full_data, green_data, i, CHART_W, CHART_H, start_time)
            
            sys.stdout.write(frame)
            sys.stdout.flush()
            
            # Reset Cursor (Height + 2 extra rows)
            sys.stdout.write(f"\r\033[{CHART_H + 2}A")
            
            time.sleep(0.04) 
            
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(f"\033[{CHART_H + 2}B")
        sys.stdout.write("\033[?25h")
        print()

if __name__ == "__main__":
    main()
