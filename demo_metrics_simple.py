#!/usr/bin/env python3
"""Simple demo to show new metrics format (no dependencies)."""

# ANSI color codes
RESET = "\033[0m"
DIM = "\033[2m"
GRAY = "\033[90m"
RED_WASHED = "\033[91m"
GREEN_WASHED = "\033[92m"
YELLOW_WASHED = "\033[93m"
ORANGE_WASHED = "\033[33m"
RED_BRIGHT = "\033[91;1m"

def format_metric(value, label, width=6):
    """Format metric with fixed width."""
    val_str = str(value)
    suffix = f" {label}"
    avail = width - len(val_str)
    if avail <= 0:
        return val_str
    if len(suffix) > avail:
        suffix = suffix[:avail]
    return f"{val_str}{suffix}".rjust(width)

def render_metrics(war=0, fail=0, err=0, skip=0, cov=0, pass_rate=0):
    """Render metrics in new format: [war | fail | err | skip | cov | pass%]"""
    
    # Colors
    war_color = YELLOW_WASHED if war > 0 else DIM
    fail_color = RED_WASHED if fail > 0 else DIM
    err_color = RED_BRIGHT if err > 0 else DIM
    skip_color = GRAY
    cov_color = GREEN_WASHED if cov >= 80 else ORANGE_WASHED if cov >= 60 else RED_WASHED if cov > 0 else DIM
    pass_color = GREEN_WASHED if pass_rate >= 95 else ORANGE_WASHED if pass_rate >= 80 else RED_WASHED if pass_rate > 0 else DIM
    
    # Format each metric
    war_str = format_metric(war, "wr", 6)
    fail_str = format_metric(fail, "fl", 6)
    err_str = format_metric(err, "er", 6)
    skip_str = format_metric(skip, "sk", 6)
    
    # Coverage special case
    if cov < 0:
        cov_str = "   n/a"
    else:
        cov_val_str = f"{cov}%"
        c_suffix = " cv"
        c_avail = 6 - len(cov_val_str)
        if len(c_suffix) > c_avail:
            c_suffix = c_suffix[:c_avail]
        cov_str = f"{cov_val_str}{c_suffix}".rjust(6)
    
    # Pass rate
    if pass_rate == 100 or pass_rate == 0:
        p_val = f"{int(pass_rate)}%"
    else:
        p_val = f"{round(pass_rate)}%"
    pass_str = p_val.rjust(6)
    
    # Build metrics string
    parts = [
        f"{war_color}{war_str}{RESET}",
        f"{fail_color}{fail_str}{RESET}",
        f"{err_color}{err_str}{RESET}",
        f"{skip_color}{skip_str}{RESET}",
        f"{cov_color}{cov_str}{RESET}",
        f"{pass_color}{pass_str}{RESET}",
    ]
    
    separator = f"{DIM}|{RESET}"
    inner = separator.join(parts)
    return f"{DIM}[{RESET}{inner}{DIM}]{RESET}"

print("=" * 70)
print("PTSD Agent v0.7.0-dev: New Metrics Format Demonstration")
print("=" * 70)
print()
print("OLD FORMAT (49 chars): [cov | war | fail | err | skip | total | pass%]")
print("NEW FORMAT (43 chars): [war | fail | err | skip | cov | pass%]")
print()
print("Changes:")
print("  • Reordered: issues first (war/fail/err/skip), then success (cov/pass%)")
print("  • Removed: total count (redundant - can be calculated)")
print("  • Saved: 6 characters (12% reduction)")
print()
print("-" * 70)
print()

test_cases = [
    ("Perfect Component          ", {"war": 0, "fail": 0, "err": 0, "skip": 0, "cov": 100, "pass_rate": 100}),
    ("Component with Warnings    ", {"war": 5, "fail": 0, "err": 0, "skip": 2, "cov": 95, "pass_rate": 100}),
    ("Component with Failures    ", {"war": 2, "fail": 3, "err": 0, "skip": 1, "cov": 85, "pass_rate": 92}),
    ("Component with Errors      ", {"war": 1, "fail": 2, "err": 3, "skip": 0, "cov": 75, "pass_rate": 87}),
    ("Mixed Issues               ", {"war": 10, "fail": 5, "err": 2, "skip": 8, "cov": 68, "pass_rate": 85}),
    ("Low Coverage               ", {"war": 0, "fail": 0, "err": 0, "skip": 0, "cov": 45, "pass_rate": 100}),
    ("No Coverage (YAML files)   ", {"war": 0, "fail": 0, "err": 0, "skip": 0, "cov": -1, "pass_rate": 0}),
]

for name, metrics in test_cases:
    rendered = render_metrics(**metrics)
    print(f"{name} {rendered}")

print()
print("-" * 70)
print()
print(f"✓ Each metric: 6 chars + label (wr, fl, er, sk, cv, %)")
print(f"✓ Total width: 43 chars (down from 49)")
print(f"✓ Benefit: More space for component/test names in narrow terminals")
print()
print("=" * 70)
