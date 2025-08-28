import re
import sys
import typer

app = typer.Typer(help="CLI tool to parse test output logs.")

@app.command()
def parse_go_failures():
    """
    Print FAIL blocks and DONE lines from test output.
    Pipe test output into this command.
    """
    in_fail_block = False

    for line in sys.stdin:
        line = re.sub(r'\x1B\[[0-9;]*[mK]', '', line)  # Strip ANSI
        line = line.rstrip('\r\n')                     # Remove carriage returns/newlines

        # Match FAIL lines
        if re.match(r'^\s*=== FAIL:', line):
            print(line)
            in_fail_block = True
            continue

        # End FAIL block on next === line
        if re.match(r'^\s*===', line):
            in_fail_block = False

        # Print indented lines after FAIL
        if in_fail_block and re.match(r'^\s+', line):
            print(line)

        # Match DONE lines (with optional indentation)
        if re.match(r'^\s*DONE', line):
            print(line)


@app.command()
def parse_go_summary():
    """
    Print only DONE summary lines.
    """
    for line in sys.stdin:
        line = re.sub(r'\x1B\[[0-9;]*[mK]', '', line)
        line = line.rstrip('\r\n')
        if re.match(r'^\s*DONE', line):
            print(line)

# Add more parsers later...
# @app.command()
# def parse_passes():
#     ...

if __name__ == "__main__":
    app()
