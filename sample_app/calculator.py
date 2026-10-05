"""A tiny command-line calculator used as the 'application under test'.

Usage:
    python sample_app/calculator.py add 2 3      -> 5
    python sample_app/calculator.py div 1 0      -> error on stderr, exit code 1
"""

import argparse
import sys


def calculate(operation: str, a: float, b: float) -> float:
    if operation == "add":
        return a + b
    if operation == "sub":
        return a - b
    if operation == "mul":
        return a * b
    if operation == "div":
        return a / b  # raises ZeroDivisionError when b == 0
    raise ValueError(f"Unknown operation: {operation}")


def format_number(value: float) -> str:
    """Show 5.0 as '5' but keep 2.5 as '2.5'."""
    return str(int(value)) if value.is_integer() else str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple calculator")
    parser.add_argument("operation", choices=["add", "sub", "mul", "div"])
    parser.add_argument("a", type=float)
    parser.add_argument("b", type=float)
    args = parser.parse_args()

    try:
        result = calculate(args.operation, args.a, args.b)
    except ZeroDivisionError:
        print("Error: cannot divide by zero", file=sys.stderr)
        return 1

    print(format_number(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
