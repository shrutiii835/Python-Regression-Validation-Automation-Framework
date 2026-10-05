"""Shared PyTest helpers."""

import pytest

from regression_framework.models import RunReport, Status, TestResult


def make_result(name="test", status=Status.PASSED, attempts=1, duration=0.5, **extra) -> TestResult:
    failures = extra.pop("failures", ["Exit code: expected 0, got 1"] if status == Status.FAILED else [])
    return TestResult(name=name, status=status, attempts=attempts, duration=duration,
                      failures=failures, source_file="test_suites/test_demo.yaml", **extra)


@pytest.fixture
def sample_report() -> RunReport:
    """A report with one result of every kind: passed, flaky, failed, skipped."""
    return RunReport(
        started_at="2026-01-01T10:00:00",
        wall_time=1.0,
        workers=2,
        git_commit="abc1234",
        git_branch="main",
        results=[
            make_result("ok_test"),
            make_result("flaky_test", attempts=2),
            make_result("broken_test", Status.FAILED, stdout="out", stderr="err"),
            make_result("skipped_test", Status.SKIPPED, attempts=0, duration=0, skip_reason="not ready"),
        ],
    )
