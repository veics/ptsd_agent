import sys
import time
import math
import shutil
import random

# --- COLORS (ANSI 256) ---
C_ORANGE_EDGE = '\033[38;5;214m'  # Bright Orange
C_GREEN_SCAT  = '\033[38;5;46m'   # Bright Green (Scattered Line)
C_RESET       = '\033[0m'

# Operation Colors (Matrix Fill)
OP_COLORS = [
    '\033[38;5;110m',  # Blue (DISCOVERY)
    '\033[38;5;108m',  # Green (EXECUTION)
    '\033[38;5;180m',  # Yellow (AI_ANALYSIS)
    '\033[38;5;174m',  # Red (AUTO_FIX)
    '\033[38;5;109m',  # Cyan (CACHE)
]

# Timeline Colors
C_TL_PROGRESS = '\033[38;5;108m'
C_TL_CURSOR   = '\033[38;5;65m'
C_TL_EMPTY    = '\033[38;5;240m'

# --- 1. SMOOTH EDGE LUT (For Orange Line) ---
# Maps (Left_Height, Right_Height) -> Smooth Curve Char
LUT_SMOOTH = [
    ['⠀', '⢀', '⢠', '⢰', '⢸'], 
    ['⡀', '⣀', '⣠', '⣰', '⣸'], 
    ['⡄', '⣄', '⣤', '⣴', '⣼'], 
    ['⡆', '⣆', '⣦', '⣶', '⣾'], 
    ['⡇', '⣇', '⣧', '⣷', '⣿'] 
]

# --- 2. SCATTERED CHAR POOLS (For Green Line) ---
# We group the user's characters by their "Visual Center of Gravity"
# to ensure the scattered line still follows the data path accurately.

# Characters that feel "Top Heavy" (for y=3.0 to 4.0)
POOL_TOP = [
    '⠛', '⠟', '⠞', '⠝', '⠜', '⠘', '⠳', '⠋', '⠉', '⠈'
]

# Characters that feel "Middle Heavy" (for y=1.5 to 3.0)
POOL_MID = [
    '⠴', '⠼', '⠯', '⠭', '⠬', '⠫', '⠪', '⠩', '⠨', '⠧', '⠦', '⠥', '⠤', '⠣', '⠢', '⠡', '⠠',
    '⠷', '⠾', '⠽', '⠻', '⠺' # The "Prominent" ones fit well in center too
]

# Characters that feel "Bottom Heavy" (for y=0.0 to 1.5)
POOL_BOT = [
    '⣤', '⣦', '⣴', '⣲', '⣱', '⣰', '⣀', '⡀', '⢀', '⠄', '⠂', '⠁'
]

# The "Prominent Dots" (Use these for stable peaks)
POOL_PEAK = ['⠿', '⠷', '⠾', '⠽', '⠻', '⠺']


def get_scattered_char(local_height):
    """
    Returns a random character that visually represents the given height.
    local_height: 0.0 (bottom) to 4.0 (top)
    """
    # 1. PEAKS: If it's very high/stable (3.5+), use a prominent dot sometimes
    if local_height > 3.5 and random.random() > 0.7:
        return random.choice(POOL_PEAK)
    
    # 2. General Mapping
    if local_height >= 2.8:
        return random.choice(POOL_TOP)
    elif local_height >= 1.2:
        return random.choice(POOL_MID)
    else:
        return random.choice(POOL_BOT)

def generate_main_data(length):
    """Generates the main volume (Solid Chart)."""
    data = []
    for x in range(length):
        # Organic wave
        val = 12 + math.sin(x * 0.1) * 8
        val += math.sin(x * 0.3) * 4
        
        # Add "Plateaus" (Discovery Phase)
        if x % 100 in range(10, 30): val = 18 + random.uniform(-1, 1)
        
        # Add "Spikes" (Auto-Fix Phase)
        if x % 60 == 0: val += 15
        
        data.append(max(1, val))
    return data

def generate_green_data(length, main_data):
    """Generates the scattered green line."""
    data = []
    for i in range(length):
        # Follow main data but offset
        base = main_data[i]
        
        # Add independent sine wave (The "AI Analysis" layer)
        offset = 6 + math.sin(i * 0.15) * 4
        
        # Add jitter to make it truly look like a scatter plot
        jitter = random.uniform(-0.5, 0.5)
        
        data.append(base + offset + jitter)
    return data

def render_frame(data_main, data_green, visible_idx, width, height):
    output = []
    
    # 1. Scale Data
    # Dynamic scaling based on the visible window + buffer
    # We look at the max of the green line since it's highest
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

            # --- LAYER 1: Main Chart (Solid + Orange Edge) ---
            m_y1, m_y2 = norm_main[i], norm_main[i+1]
            
            char_final = " "
            color_final = C_RESET
            
            if m_y1 >= row_top and m_y2 >= row_top:
                # Solid Fill
                char_final = "⣿"
                color_final = random.choice(OP_COLORS)
            elif m_y1 < row_bottom and m_y2 < row_bottom:
                # Empty
                char_final = " "
            else:
                # Orange Smooth Edge (LUT)
                ly1 = int(max(0, min(4, m_y1 - row_bottom)))
                ly2 = int(max(0, min(4, m_y2 - row_bottom)))
                char_final = LUT_SMOOTH[ly1][ly2]
                color_final = C_ORANGE_EDGE

            # --- LAYER 2: Green Scattered Overlay ---
            # We map the exact height to a textured character
            g_y = norm_green[i]
            
            # If the green point falls in this row
            if row_bottom <= g_y < row_top:
                local_h = g_y - row_bottom
                
                # Get a "Scattered" character based on height
                # This uses your specific list (⠴, ⠼, ⠛, etc.)
                scatter_char = get_scattered_char(local_h)
                
                # Overlay it
                char_final = scatter_char
                color_final = C_GREEN_SCAT

            line_buffer += f"{color_final}{char_final}"
        
        output.append(line_buffer + C_RESET)
    
    # 3. Render Timeline
    progress = C_TL_PROGRESS + ("━" * (visible_idx - 1))
    cursor = C_TL_CURSOR + "█"
    empty = C_TL_EMPTY + ("┄" * (width - visible_idx))
    output.append(progress + cursor + empty + C_RESET)
    
    return "\n".join(output)

def main():
    # Setup
    try:
        cols, rows = shutil.get_terminal_size()
    except:
        cols, rows = 80, 24
        
    CHART_ROWS = 6 # Taller to show off the layers
    WIDTH = cols - 1
    
    # Data
    full_data = generate_main_data(WIDTH)
    green_data = generate_green_data(WIDTH, full_data)
    
    sys.stdout.write("\033[?25l") # Hide Cursor
    
    try:
        # Loop
        for i in range(1, WIDTH):
            frame = render_frame(full_data, green_data, i, WIDTH, CHART_ROWS)
            sys.stdout.write(frame)
            sys.stdout.flush()
            
            # Reset Cursor (Rows + Timeline)
            sys.stdout.write(f"\r\033[{CHART_ROWS + 1}A")
            
            time.sleep(0.04)
            
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(f"\033[{CHART_ROWS + 1}B\033[?25h\n")

if __name__ == "__main__":
    main()
