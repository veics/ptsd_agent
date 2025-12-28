import sys
import time
import math
import shutil
import random

# --- COLORS ---
C_ORANGE_EDGE = '\033[38;5;214m'  # Bright Orange
C_GREEN_DOTS  = '\033[38;5;46m'   # Bright Green (Crisp Dotted Line)
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

# --- 1. SMOOTH ORANGE LUT ---
LUT_SMOOTH = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

# --- 2. STRICT SINGLE-ROW DOT POOLS ---
# These pools ensure we NEVER pick a char that spans multiple vertical rows.
POOL_R3 = ['⠁', '⠈', '⠉']  # Top of cell
POOL_R2 = ['⠂', '⠐', '⠒']  # Upper Mid
POOL_R1 = ['⠄', '⠠', '⠤']  # Lower Mid
POOL_R0 = ['⡀', '⢀', '⣀']  # Bottom

def get_crisp_scatter_char(local_height):
    """
    local_height: 0.0 to 4.0
    Returns a char that exists ONLY at that specific vertical slice.
    """
    # Quantize height to 0, 1, 2, 3
    row = int(local_height)
    if row >= 3: return random.choice(POOL_R3)
    if row == 2: return random.choice(POOL_R2)
    if row == 1: return random.choice(POOL_R1)
    return random.choice(POOL_R0)

def generate_main_data(length):
    """Generates the main volume (Solid Chart)."""
    data = []
    for x in range(length):
        # Base Curve
        val = 12 + math.sin(x * 0.1) * 8
        val += math.sin(x * 0.3) * 4
        
        # Add "Plateaus"
        if x % 100 in range(10, 30): val = 18 + random.uniform(-0.5, 0.5)
        
        # Add "Spikes"
        if x % 50 == 0: val += 12
        
        data.append(max(1, val))
    return data

def generate_green_data(length, main_data):
    """Generates the green scattered line."""
    data = []
    for i in range(length):
        base = main_data[i]
        
        # Offset slightly above main chart
        offset = 5 + math.sin(i * 0.2) * 3
        
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

            # --- LAYER 2: Green Scattered Line ---
            g_y = norm_green[i]
            
            # Check if the green POINT falls in this row
            if row_bottom <= g_y < row_top:
                local_h = g_y - row_bottom
                
                # Use the STRICT pool to avoid thickness
                scatter_char = get_crisp_scatter_char(local_h)
                
                char_final = scatter_char
                color_final = C_GREEN_DOTS

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
