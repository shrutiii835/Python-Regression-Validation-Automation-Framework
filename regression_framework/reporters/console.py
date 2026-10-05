"""Colourful, readable console output: live progress and the final summary."""

import os
import sys
from pathlib import Path

from regression_framework.models import RunReport, Status, TestResult

GREEN, RED, YELLOW, CYAN, DIM, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[36m", "\033[2m", "\033[1m", "\033[0m"
)


def use_color() -> bool:
    """Only colour real terminals, and respect the NO_COLOR convention (https://no-color.org)."""
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def paint(text: str, *styles: str) -> str:
    return "".join(styles) + text + RESET if use_color() else text


def print_run_header(test_count: int, workers: int, retries: int) -> None:
    print(paint(f"\nRunning {test_count} test(s) with {workers} worker(s), {retries} retr(y/ies)\n", BOLD))


def print_progress(result: TestResult) -> None:
    """Print one line as soon as a test finishes."""
    if result.status == Status.SKIPPED:
        label, extra = paint(" SKIP ", DIM), paint(result.skip_reason, DIM)
    elif result.is_flaky:
        label, extra = paint("FLAKY ", YELLOW, BOLD), paint(f"passed on attempt {result.attempts}", YELLOW)
    elif result.passed:
        label, extra = paint(" PASS ", GREEN, BOLD), ""
    else:
        label, extra = paint(" FAIL ", RED, BOLD), paint(result.failures[0].splitlines()[0], RED)
    print(f"  {label} {result.name:<42} {paint(f'{result.duration:6.2f}s', DIM)}  {extra}")


def print_summary(report: RunReport, report_paths: dict[str, Path]) -> None:
    summary = report.summary
    line = "=" * 72
    print(f"\n{line}")

    failed = [r for r in report.results if r.failed]
    if failed:
        print(paint("Failures\n", RED, BOLD))
        for result in failed:
            print(paint(f"  {result.name}", RED, BOLD) + paint(f"  ({result.source_file})", DIM))
            print(paint(f"    $ {result.command}", DIM))
            for message in result.failures:
                for i, text in enumerate(message.splitlines()):
                    print(f"    {'-' if i == 0 else ' '} {color_diff_line(text)}")
            print()

    if report.comparison:
        print_comparison(report)

    status = paint(" PASSED ", GREEN, BOLD) if summary["failed"] == 0 else paint(" FAILED ", RED, BOLD)
    print(
        f"{status} {summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['flaky']} flaky, {summary['skipped']} skipped  "
        f"| pass rate {summary['pass_rate']}%"
    )
    print(
        paint(f"Finished in {summary['wall_time']}s (total test time {summary['test_time']}s, "
              f"{summary['speedup']}x faster with {report.workers} workers)", DIM)
    )
    run_label = f"run #{report.run_number}" if report.run_number else "history disabled"
    print(paint(f"Git {report.git_branch}@{report.git_commit} | {run_label}", DIM))
    print(line)
    for name, path in report_paths.items():
        print(f"  {name:<9} {path}")
    print()


def print_comparison(report: RunReport) -> None:
    comparison = report.comparison
    print(paint(f"Compared with run #{comparison.previous_run}", BOLD))
    if comparison.new_failures:
        names = ", ".join(comparison.new_failures)
        print(paint(f"  {len(comparison.new_failures)} NEW FAILURE(S): {names}", RED, BOLD))
    if comparison.fixed:
        print(paint(f"  {len(comparison.fixed)} fixed: {', '.join(comparison.fixed)}", GREEN))
    if comparison.still_failing:
        print(paint(f"  {len(comparison.still_failing)} still failing: {', '.join(comparison.still_failing)}", YELLOW))
    if comparison.new_tests:
        print(paint(f"  {len(comparison.new_tests)} new test(s)", CYAN))
    if not (comparison.new_failures or comparison.fixed or comparison.still_failing):
        print(paint("  No changes in test outcomes", DIM))
    print()


def color_diff_line(text: str) -> str:
    if text.startswith("+") and not text.startswith("+++"):
        return paint(text, GREEN)
    if text.startswith("-") and not text.startswith("---"):
        return paint(text, RED)
    if text.startswith("@@"):
        return paint(text, CYAN)
    return text


def print_history(runs: list[dict]) -> None:
    """Print recent runs as a table (used by `regress history`)."""
    if not runs:
        print("No runs recorded yet. Run `regress run` first.")
        return
    header = (f"{'Run':>5}  {'Started':<19}  {'Branch@Commit':<24} "
              f"{'Total':>5} {'Pass':>5} {'Fail':>5} {'Flaky':>5} {'Rate':>7} {'Time':>7}")
    print(paint(header, BOLD))
    for run in reversed(runs):  # newest first
        rate = paint(f"{run['pass_rate']:>6}%", GREEN if run["failed"] == 0 else RED)
        git_label = f"{run['git_branch']}@{run['git_commit']}"[:24]
        print(
            f"{run['id']:>5}  {run['started_at'][:19]:<19}  {git_label:<24} "
            f"{run['total']:>5} {run['passed']:>5} {run['failed']:>5} {run['flaky']:>5} "
            f"{rate} {run['wall_time']:>6.2f}s"
        )
