#!/usr/bin/env python3
"""Static demo showing EXACTLY what the chart should look like - FULL WIDTH!"""

import shutil

# ANSI colors
RESET = '\033[0m'
GRAY = '\033[38;5;240m'
BLUE = '\033[38;5;110m'
GREEN = '\033[38;5;108m'
YELLOW = '\033[38;5;180m'
RED = '\033[38;5;174m'
CYAN = '\033[38;5;109m'

# Braille chars
FULL = '⣿'
EDGE = '⣸'
SPARSE = '⠊⠑⠒⠱⠴⠳'

# Get terminal width
tw = shutil.get_terminal_size().columns
data_width = tw - 10  # Leave margin for Y-axis

print("\n" + "="*tw)
print(f"TERMINAL WIDTH: {tw} chars")
print(f"CHART WIDTH: {data_width} chars")
print("="*tw + "\n")

# Build chart lines - FULL WIDTH!
lines = []

# Level 12 - CONTINUOUS YELLOW CURVE  
line12 = f"{GRAY} 12 ┃{RESET}"
for i in range(data_width):
    line12 += YELLOW + SPARSE[i % len(SPARSE)] + RESET
lines.append(line12)

# Level 9
line9 = f"{GRAY}  9 ┃{RESET}"
for i in range(data_width):
    if i % 10 < 6:  # Show blocks
        if i % 10 == 4:  # Edge
            line9 += GREEN + EDGE + RESET
        else:
            line9 += GREEN + FULL + RESET
    else:
        line9 += " "
lines.append(line9)

# Level 6
line6 = f"{GRAY}  6 ┃{RESET}"
for i in range(data_width):
    if i % 8 < 5:
        if i % 8 == 3:
            line6 += BLUE + EDGE + RESET
        else:
            line6 += BLUE + FULL + RESET
    else:
        line6 += " "
lines.append(line6)

# Level 3
line3 = f"{GRAY}  3 ┃{RESET}"
for i in range(data_width):
    if i < data_width - 5:
        if i % 6 == 2:
            line3 += RED + EDGE + RESET
        else:
            line3 += RED + FULL + RESET
    else:
        line3 += " "
lines.append(line3)

# Level 1
line1 = f"{GRAY}  1 ┃{RESET}"
for i in range(data_width):
    if i % 5 == 1:
        line1 += CYAN + EDGE + RESET
    else:
        line1 += CYAN + FULL + RESET
lines.append(line1)

# Print chart
for line in lines:
    print(line)

# Timeline - FULL WIDTH with GREEN
tl = f"{GRAY}    ┗━━{RESET}"
green_width = min(data_width - 10, 30)
for i in range(green_width):
    tl += f"{GREEN}━{RESET}"
tl += " "  # Gap
remaining = tw - len("    ┗━━") - green_width - 1 - 1
if remaining > 0:
    tl += f"{GRAY}{'━' * remaining}┛{RESET}"
else:
    tl += f"{GRAY}┛{RESET}"
print(tl)

print("\n" + "="*tw)
print("WHAT YOU SHOULD SEE:")
print(f"  - {YELLOW}YELLOW{RESET} continuous curve at level 12")
print(f"  - {BLUE}BLUE{RESET}, {GREEN}GREEN{RESET}, {RED}RED{RESET}, {CYAN}CYAN{RESET} colored blocks")
print(f"  - {EDGE} Crisp edges at transitions")
print(f"  - Chart spanning {data_width} characters wide!")
print("="*tw + "\n")

print("If you don't see colors, your terminal may not support ANSI colors.")
print("Try running in a different terminal (iTerm2, Terminal.app, etc.)\n")
