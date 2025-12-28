#!/bin/bash

# Paleta de culori pentru coloane (Washed / Muted)
C1=$(printf '\033[38;5;110m') # Discovery (Blue)
C2=$(printf '\033[38;5;108m') # Execution (Green)
C3=$(printf '\033[38;5;180m') # Analysis (Yellow)
C4=$(printf '\033[38;5;174m') # Auto-Fix (Red)
GRAY=$(printf '\033[38;5;240m')
RESET=$(printf '\033[0m')

draw_column_graph() {
    clear
    printf "\n  %sSystem Threads - Column Based UI%s\n\n" "${GRAY}" "${RESET}"

    # Matricea graficului (simulăm 5 coloane cu înălțimi diferite)
    # Coloana:  1   2   3   4   5
    # Culoare: C1  C2  C3  C2  C4
    
    # Rând 12 (Pulse/Top)
    printf " 12 ┃       %s⣿%s\n" "$C3" "$RESET"

    # Rând 9
    printf "  9 ┃     %s⣿%s%s⣿%s%s⣿%s\n" "$C2" "$RESET" "$C3" "$RESET" "$C2" "$RESET"

    # Rând 7
    printf "  7 ┃   %s⣿%s%s⣿%s%s⣿%s%s⣿%s%s⣿%s\n" "$C1" "$RESET" "$C2" "$RESET" "$C3" "$RESET" "$C2" "$RESET" "$C4" "$RESET"

    # Rând 4
    printf "  4 ┃  %s⣿%s%s⣿%s%s⣿%s%s⣿%s%s⣿%s%s⣿%s%s⣿%s\n" "$C1" "$RESET" "$C1" "$RESET" "$C2" "$RESET" "$C3" "$RESET" "$C2" "$RESET" "$C4" "$RESET" "$C4" "$RESET"

    # Rând 0.0
    printf "0.0 ┃ %s⣿%s%s⣿%s%s⣿%s%s⣿%s%s⣿%s%s⣿%s%s⣿%s%s⣿%s%s⣿%s\n" "$C1" "$RESET" "$C1" "$RESET" "$C1" "$RESET" "$C2" "$RESET" "$C3" "$RESET" "$C2" "$RESET" "$C4" "$RESET" "$C4" "$RESET" "$C4" "$RESET"

    printf "    %s┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%s\n" "${GRAY}" "${RESET}"
    printf "      00      01      02      03\n"
}

draw_column_graph

