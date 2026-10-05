"""Run test cases, with retries and parallel execution."""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from regression_framework.executor import command_to_string, run_command
from regression_framework.logger import get_logger
from regression_framework.models import Status, TestCase, TestResult
from regression_framework.validators import validate

logger = get_logger(__name__)


@dataclass
class RunOptions:
    """Settings that control how tests are executed."""

    workers: int = 1
    retries: int = 0
    retry_delay: float = 0.0
    cwd: Path = Path(".")
    update_snapshots: bool = False


def run_single_test(test: TestCase, options: RunOptions | None = None) -> TestResult:
    """Run one test. If it fails, try again up to `retries` more times."""
    options = options or RunOptions()
    result = TestResult(
        name=test.name,
        status=Status.SKIPPED,
        command=command_to_string(test.command),
        description=test.description,
        tags=list(test.tags),
        source_file=test.source_file,
    )

    if test.skip:
        result.skip_reason = test.skip_reason
        logger.info("SKIPPED %s (%s)", test.name, result.skip_reason)
        return result

    retries = test.retries if test.retries is not None else options.retries
    max_attempts = retries + 1

    for attempt in range(1, max_attempts + 1):
        # Every test process can see its own name and attempt number.
        env = {**test.env, "REGRESS_TEST_NAME": test.name, "REGRESS_ATTEMPT": str(attempt)}
        command_result = run_command(test.command, test.timeout, options.cwd, test.stdin, env)
        failures = validate(test, command_result, options.cwd, options.update_snapshots)

        result.attempts = attempt
        result.duration += command_result.duration
        if not failures:
            break
        if attempt < max_attempts:
            logger.info("RETRY   %s (attempt %d/%d failed: %s)",
                        test.name, attempt, max_attempts, failures[0].splitlines()[0])
            time.sleep(options.retry_delay)

    result.status = Status.FAILED if failures else Status.PASSED
    result.exit_code = command_result.exit_code
    result.stdout = command_result.stdout
    result.stderr = command_result.stderr
    result.failures = failures
    result.duration = round(result.duration, 3)

    if result.passed:
        logger.info("PASSED  %s (%.2fs, attempts=%d)", test.name, result.duration, result.attempts)
    else:
        logger.info("FAILED  %s -> %s", test.name, " | ".join(f.splitlines()[0] for f in failures))
    return result


def run_all_tests(
    test_cases: list[TestCase],
    options: RunOptions | None = None,
    on_result: Callable[[TestResult], None] | None = None,
) -> list[TestResult]:
    """Run every test in parallel and return results in the same order as test_cases.

    `on_result` is called (from the main thread) as soon as each test finishes,
    which is how the console shows live progress.

    Threads work well here: each test spends its time waiting on a separate
    subprocess, so Python's GIL is not a bottleneck.
    """
    options = options or RunOptions()
    logger.info("Running %d test(s) with %d worker(s)", len(test_cases), options.workers)

    with ThreadPoolExecutor(max_workers=options.workers, thread_name_prefix="worker") as pool:
        futures = [pool.submit(run_single_test, test, options) for test in test_cases]
        for future in as_completed(futures):
            if on_result:
                on_result(future.result())
        return [future.result() for future in futures]
