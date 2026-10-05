import time

from regression_framework.models import Status, TestCase
from regression_framework.runner import RunOptions, run_all_tests, run_single_test

# Fails on the first `N` attempts, then passes. Uses REGRESS_ATTEMPT, set by the runner.
FAILS_UNTIL_ATTEMPT = "import os, sys; sys.exit(0 if int(os.environ['REGRESS_ATTEMPT']) > {n} else 1)"


def python(code: str) -> list[str]:
    return ["python", "-c", code]


def test_passing_test():
    test = TestCase(name="ok", command=python("print('hi')"), expected_output="hi")
    result = run_single_test(test)

    assert result.status == Status.PASSED
    assert result.attempts == 1
    assert result.is_flaky is False
    assert result.command.startswith("python -c")


def test_failing_test_without_retries():
    test = TestCase(name="bad", command=python("print('hi')"), expected_output="bye")
    result = run_single_test(test, RunOptions(retries=0))

    assert result.status == Status.FAILED
    assert result.attempts == 1
    assert "Output mismatch" in result.failures[0]


def test_retry_makes_flaky_test_pass():
    test = TestCase(name="flaky", command=python(FAILS_UNTIL_ATTEMPT.format(n=1)))
    result = run_single_test(test, RunOptions(retries=2))

    assert result.passed
    assert result.attempts == 2
    assert result.is_flaky


def test_retries_are_limited():
    test = TestCase(name="always_fails", command=python("exit(1)"))
    result = run_single_test(test, RunOptions(retries=2))

    assert result.failed
    assert result.attempts == 3  # 1 run + 2 retries


def test_per_test_retries_override_options():
    test = TestCase(name="t", command=python(FAILS_UNTIL_ATTEMPT.format(n=2)), retries=2)
    assert run_single_test(test, RunOptions(retries=0)).passed


def test_skipped_test_is_not_run():
    test = TestCase(name="t", command="this_program_does_not_exist", skip="not ready yet")
    result = run_single_test(test)

    assert result.status == Status.SKIPPED
    assert result.skip_reason == "not ready yet"
    assert result.attempts == 0


def test_test_name_is_passed_to_the_process():
    test = TestCase(name="my_test", command=python("import os; print(os.environ['REGRESS_TEST_NAME'])"),
                    expected_output="my_test")
    assert run_single_test(test).passed


def test_run_all_tests_keeps_order_and_reports_progress():
    tests = [TestCase(name=f"t{i}", command=python(f"print({i})"), expected_output=str(i)) for i in range(5)]
    seen = []

    results = run_all_tests(tests, RunOptions(workers=3), on_result=lambda r: seen.append(r.name))

    assert [r.name for r in results] == ["t0", "t1", "t2", "t3", "t4"]
    assert sorted(seen) == ["t0", "t1", "t2", "t3", "t4"]
    assert all(r.passed for r in results)


def test_parallel_is_faster_than_sequential():
    tests = [TestCase(name=f"sleep{i}", command=python("import time; time.sleep(0.5)")) for i in range(4)]

    start = time.perf_counter()
    run_all_tests(tests, RunOptions(workers=4))
    elapsed = time.perf_counter() - start

    # Four 0.5s tests in sequence would take at least 2 seconds.
    assert elapsed < 1.8
