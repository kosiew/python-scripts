import re
import sys

def parse_line(line):
    # Extract fields from critcmp-style line
    parts = re.split(r'\s{2,}', line.strip())
    if len(parts) < 3:
        return None
    name, main, short = parts[:3]
    try:
        main_time = float(re.findall(r'([\d.]+)', main)[0])
        short_time = float(re.findall(r'([\d.]+)', short)[0])
        return name, main_time, short_time
    except:
        return None

def highlight_diff(main, short):
    diff = (short - main) / main * 100
    arrow = "↘" if diff < 0 else "↗"
    if abs(diff) < 0.5:
        color = "\033[90m"  # gray
    elif diff < 0:
        color = "\033[92m"  # green
    else:
        color = "\033[91m"  # red
    return f"{color}{arrow} {diff:+.2f}%\033[0m"

def main():
    lines = sys.stdin.read().splitlines()
    print(f"{'Benchmark':50} {'Change':>10}")
    print("-" * 62)
    for line in lines:
        parsed = parse_line(line)
        if parsed:
            name, main_val, short_val = parsed
            diff = highlight_diff(main_val, short_val)
            print(f"{name:50} {diff:>10}")

if __name__ == "__main__":
    main()
