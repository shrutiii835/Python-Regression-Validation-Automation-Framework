"""Compare expected results (from the TestCase) with actual results (from the run).

Each check is a small function that returns a list of failure messages
(an empty list means "this check passed"). To add a new kind of check,
write a function with the same signature and add it to CHECKS.
"""

import difflib
import json
import re
from pathlib import Path

from regression_framework.executor import CommandResult
from regression_framework.models import TestCase


def make_diff(expected: str, actual: str, expected_name: str = "expected", actual_name: str = "actual") -> str:
    """Return a unified diff (like `git diff`) between two texts."""
    lines = difflib.unified_diff(
        expected.splitlines(), actual.splitlines(), fromfile=expected_name, tofile=actual_name, lineterm=""
    )
    return "\n".join(lines)


def normalize(text: str) -> str:
    """Ignore trailing spaces and blank lines at the end, which rarely matter."""
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


# ---------------------------------------------------------------- individual checks

def check_exit_code(test: TestCase, result: CommandResult) -> list[str]:
    if result.exit_code != test.expected_exit_code:
        return [f"Exit code: expected {test.expected_exit_code}, got {result.exit_code}"]
    return []


def check_exact_output(test: TestCase, result: CommandResult) -> list[str]:
    if test.expected_output is None:
        return []
    expected, actual = normalize(str(test.expected_output)), normalize(result.stdout)
    if expected == actual:
        return []
    if "\n" in expected or "\n" in actual:
        return ["Output mismatch:\n" + make_diff(expected, actual)]
    return [f"Output mismatch: expected {expected!r}, got {actual!r}"]


def check_output_contains(test: TestCase, result: CommandResult) -> list[str]:
    return [f"Output does not contain {str(text)!r}"
            for text in test.expected_output_contains if str(text) not in result.stdout]


def check_stderr_contains(test: TestCase, result: CommandResult) -> list[str]:
    return [f"Stderr does not contain {str(text)!r}"
            for text in test.expected_stderr_contains if str(text) not in result.stderr]


def check_output_regex(test: TestCase, result: CommandResult) -> list[str]:
    if test.expected_output_regex is None:
        return []
    if re.search(test.expected_output_regex, result.stdout, re.MULTILINE):
        return []
    return [f"Output does not match pattern {test.expected_output_regex!r}"]


def check_json_output(test: TestCase, result: CommandResult) -> list[str]:
    if test.expected_json is None:
        return []
    try:
        actual = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ["Output is not valid JSON"]
    return json_mismatches(test.expected_json, actual)


def check_duration(test: TestCase, result: CommandResult) -> list[str]:
    if test.max_duration is not None and result.duration > test.max_duration:
        return [f"Too slow: took {result.duration:.2f}s, limit is {test.max_duration:.2f}s (performance regression)"]
    return []


CHECKS = [
    check_exit_code,
    check_exact_output,
    check_output_contains,
    check_output_regex,
    check_json_output,
    check_stderr_contains,
    check_duration,
]


# ---------------------------------------------------------------- helpers

def json_mismatches(expected, actual, path: str = "$") -> list[str]:
    """Check that `actual` contains everything in `expected` (extra keys are allowed).

    `path` describes where we are, e.g. "$.items[0].price", so messages are precise.
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected an object, got {json.dumps(actual)}"]
        problems = []
        for key, expected_value in expected.items():
            if key not in actual:
                problems.append(f"{path}.{key}: missing from output")
            else:
                problems.extend(json_mismatches(expected_value, actual[key], f"{path}.{key}"))
        return problems

    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [f"{path}: expected a list of {len(expected)} item(s), got {json.dumps(actual)}"]
        problems = []
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual, strict=True)):
            problems.extend(json_mismatches(expected_item, actual_item, f"{path}[{index}]"))
        return problems

    if expected != actual:
        return [f"{path}: expected {json.dumps(expected)}, got {json.dumps(actual)}"]
    return []


def check_snapshot(test: TestCase, result: CommandResult, base_dir: Path, update: bool) -> list[str]:
    """Compare stdout with a saved 'golden' file. With update=True, (re)write the file instead."""
    if not test.expected_output_file:
        return []
    path = base_dir / test.expected_output_file

    if update:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.stdout, encoding="utf-8")
        return []

    if not path.is_file():
        return [f"Snapshot file not found: {test.expected_output_file} (run with --update-snapshots to create it)"]

    expected = normalize(path.read_text(encoding="utf-8"))
    actual = normalize(result.stdout)
    if expected == actual:
        return []
    diff = make_diff(expected, actual, f"snapshot: {test.expected_output_file}", "actual output")
    return [f"Output differs from snapshot {test.expected_output_file}:\n{diff}"]


# ---------------------------------------------------------------- entry point

def validate(
    test: TestCase,
    result: CommandResult,
    base_dir: str | Path = ".",
    update_snapshots: bool = False,
) -> list[str]:
    """Run every check and return all failure messages. An empty list means PASS."""
    if result.timed_out:
        return [f"Timed out after {test.timeout} seconds"]

    failures: list[str] = []
    for check in CHECKS:
        failures.extend(check(test, result))
    failures.extend(check_snapshot(test, result, Path(base_dir), update_snapshots))
    return failures
