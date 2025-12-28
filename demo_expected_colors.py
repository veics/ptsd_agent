#!/usr/bin/env python3
"""Simple static demo showing what the chart SHOULD look like with colors."""

# ANSI colors
RESET = '\033[0m'
GRAY = '\033[38;5;240m'
BLUE = '\033[38;5;110m'    # Discovery
GREEN = '\033[38;5;108m'   # Execution  
YELLOW = '\033[38;5;180m'  # AI
RED = '\033[38;5;174m'     # Fix
CYAN = '\033[38;5;109m'    # Cache
BLOCK = '⣿'

print("\n" + "="*80)
print("EXPECTED OUTPUT - With Stacked Colors")
print("="*80 + "\n")

# Example: Show a single column with stacked operations
print("Single column with Discovery(2) + Execution(4) threads:")
print(f"Level 6: {GREEN}{BLOCK}{RESET}  (Execution layer)")
print(f"Level 3: {GREEN}{BLOCK}{RESET}  (Execution layer)")
print(f"Level 1: {BLUE}{BLOCK}{RESET}  (Discovery layer)")
print()

# Show full chart example
print("Full chart example (what you should see):")
print(f" 12 {GRAY}┃{RESET}       {YELLOW}{BLOCK}{RESET}          ")
print(f"  6 {GRAY}┃{RESET}  {BLUE}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{YELLOW}{BLOCK}{YELLOW}{BLOCK}{YELLOW}{BLOCK}{RED}{BLOCK}{RED}{BLOCK}{RESET}    ")
print(f"  3 {GRAY}┃{RESET} {BLUE}{BLOCK}{BLUE}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{YELLOW}{BLOCK}{YELLOW}{BLOCK}{RED}{BLOCK}{RED}{BLOCK}{RED}{BLOCK}{CYAN}{BLOCK}{CYAN}{BLOCK}{CYAN}{BLOCK}{RESET}  ")
print(f"  1 {GRAY}┃{RESET}{BLUE}{BLOCK}{BLUE}{BLOCK}{BLUE}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{GREEN}{BLOCK}{YELLOW}{BLOCK}{YELLOW}{BLOCK}{RED}{BLOCK}{RED}{BLOCK}{CYAN}{BLOCK}{CYAN}{BLOCK}{CYAN}{BLOCK}{CYAN}{BLOCK}{RESET}")
print(f"    {GRAY}┗━━{GREEN}━━━━━━━━━━━━━━━━━━━━{RESET} {GRAY}{'━'*20}┛{RESET}")
print()

print("Notice:")
print(f"  - Bars change color = {BLUE}{BLOCK}{RESET} Blue → {GREEN}{BLOCK}{RESET} Green → {YELLOW}{BLOCK}{RESET} Yellow → {RED}{BLOCK}{RESET} Red → {CYAN}{BLOCK}{RESET} Cyan")
print(f"  - Timeline is {GREEN}GREEN{RESET} (not grey!)")
print(f"  - Each vertical column shows MULTIPLE colors stacked")
print()
print("="*80 + "\n")

# Now test if running the demo shows this
print("If you see different colors above, run: python demo_chart_proposal.py")
print("The animated demo should show similar color changes!")
