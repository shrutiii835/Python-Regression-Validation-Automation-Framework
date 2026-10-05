"""The `regress` command-line tool.

    regress run                       run all tests (settings from config/config.yaml)
    regress run --tags smoke -k order run a subset
    regress run --update-snapshots    re-record golden snapshot files
    regress list                      show which tests would run
    regress history                   show recent runs and pass rates

Exit codes: 0 = all tests passed, 1 = a test failed (or none found), 2 = setup error.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from regression_framework import __version__
from regression_framework.config_loader import load_config
from regression_framework.discovery import discover_tests
from regression_framework.git_info import get_git_info
from regression_framework.history import HistoryStore, compare_with_previous
from regression_framework.logger import get_logger, setup_logging
from regression_framework.models import RunReport, TestCase
from regression_framework.reporters import console, write_all_reports
from regression_framework.runner import RunOptions, run_all_tests

logger = get_logger(__name__)

EXIT_OK, EXIT_TESTS_FAILED, EXIT_SETUP_ERROR = 0, 1, 2


# ---------------------------------------------------------------- argument parsing

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="regress", description="Config-driven regression testing framework.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # Options shared by several commands ("parent" parsers avoid repeating them).
    config_options = argparse.ArgumentParser(add_help=False)
    config_options.add_argument("--config", default="config/config.yaml", help="YAML or JSON config file")

    selection = argparse.ArgumentParser(add_help=False)
    selection.add_argument("--test-dir", help="folder containing test suite files")
    selection.add_argument("--tags", nargs="+", help="only tests with at least one of these tags")
    selection.add_argument("-k", dest="name_filter", help="only tests whose name contains this text")

    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", parents=[config_options, selection], help="run the regression tests")
    run.add_argument("--workers", type=int, help="number of tests to run in parallel")
    run.add_argument("--retries", type=int, help="extra attempts for a failing test")
    run.add_argument("--update-snapshots", action="store_true", help="re-record golden snapshot files")
    run.add_argument("--no-history", action="store_true", help="don't save this run to the history database")
    run.add_argument("-v", "--verbose", action="store_true", help="show detailed log messages")

    commands.add_parser("list", parents=[config_options, selection], help="list tests without running them")

    history = commands.add_parser("history", parents=[config_options], help="show recent runs")
    history.add_argument("--limit", type=int, default=15, help="number of runs to show")

    return parser


def load_settings(args: argparse.Namespace) -> dict:
    """Read the config file, then let command-line options override it."""
    config = load_config(args.config)
    overrides = {
        "test_dir": getattr(args, "test_dir", None),
        "tags": getattr(args, "tags", None),
        "workers": getattr(args, "workers", None),
        "retries": getattr(args, "retries", None),
    }
    config.update({key: value for key, value in overrides.items() if value is not None})
    if config["workers"] < 1 or config["retries"] < 0:
        raise ValueError("--workers must be >= 1 and --retries must be >= 0")
    return config


def select_tests(config: dict, args: argparse.Namespace) -> list[TestCase]:
    return discover_tests(config["test_dir"], config["default_timeout"], config["tags"], args.name_filter)


# ---------------------------------------------------------------- commands

def cmd_run(args: argparse.Namespace) -> int:
    config = load_settings(args)
    log_file = setup_logging(config["log_dir"], "DEBUG" if args.verbose else config["log_level"])
    tests = select_tests(config, args)
    if not tests:
        print("No tests found - check 'test_dir', --tags and -k.", file=sys.stderr)
        return EXIT_TESTS_FAILED

    options = RunOptions(
        workers=config["workers"],
        retries=config["retries"],
        retry_delay=config["retry_delay"],
        cwd=Path.cwd(),
        update_snapshots=args.update_snapshots,
    )
    console.print_run_header(len(tests), options.workers, options.retries)

    started_at = datetime.now().isoformat(timespec="seconds")
    start = time.perf_counter()
    results = run_all_tests(tests, options, on_result=console.print_progress)
    git = get_git_info()

    report = RunReport(
        started_at=started_at,
        wall_time=time.perf_counter() - start,
        results=results,
        workers=options.workers,
        git_commit=git["commit"],
        git_branch=git["branch"],
    )

    if config["history_db"] and not args.no_history:
        store = HistoryStore(config["history_db"])
        report.comparison = compare_with_previous(store.last_run(), results)
        report.run_number = store.save_run(report)
        report.trend = store.recent_runs(limit=20)

    report_paths = write_all_reports(report, config["report_dir"])
    report_paths["Log"] = log_file
    console.print_summary(report, report_paths)

    return EXIT_OK if report.summary["failed"] == 0 else EXIT_TESTS_FAILED


def cmd_list(args: argparse.Namespace) -> int:
    config = load_settings(args)
    setup_logging(config["log_dir"], config["log_level"])
    tests = select_tests(config, args)
    for test in tests:
        skip = f"  [skip: {test.skip_reason}]" if test.skip else ""
        print(f"{test.name:<42} {', '.join(test.tags):<32} {test.source_file}{skip}")
    print(f"\n{len(tests)} test(s)")
    return EXIT_OK


def cmd_history(args: argparse.Namespace) -> int:
    config = load_settings(args)
    if not config["history_db"]:
        print("History is disabled ('history_db' is empty in the config).")
        return EXIT_OK
    console.print_history(HistoryStore(config["history_db"]).recent_runs(args.limit))
    return EXIT_OK


COMMANDS = {"run": cmd_run, "list": cmd_list, "history": cmd_history}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except (FileNotFoundError, ValueError) as error:
        print(f"Setup error: {error}", file=sys.stderr)
        return EXIT_SETUP_ERROR


if __name__ == "__main__":
    sys.exit(main())
