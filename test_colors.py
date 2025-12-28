#!/usr/bin/env python3
"""Quick color test to verify ANSI colors work."""

# ANSI colors
RESET = '\033[0m'
BLUE = '\033[38;5;110m'
GREEN = '\033[38;5;108m'
YELLOW = '\033[38;5;180m'
RED = '\033[38;5;174m'
CYAN = '\033[38;5;109m'
BLOCK = '⣿'

print("\n" + "="*60)
print("COLOR TEST - Each block should be a different color:")
print("="*60)
print(f"\n{BLUE}{BLOCK}{RESET} Blue (Discovery)")
print(f"{GREEN}{BLOCK}{RESET} Green (Execution)")  
print(f"{YELLOW}{BLOCK}{RESET} Yellow (AI)")
print(f"{RED}{BLOCK}{RESET} Red (Fix)")
print(f"{CYAN}{BLOCK}{RESET} Cyan (Cache)")
print("\nStacked example:")
print(f"{BLUE}{BLOCK}{GREEN}{BLOCK}{YELLOW}{BLOCK}{RED}{BLOCK}{CYAN}{BLOCK}{RESET}")
print("\n" + "="*60 + "\n")
