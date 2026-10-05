"""Run the YAML/JSON regression suites through PyTest.

This is an alternative to `regress run`. Each suite test becomes its own
PyTest test, so you get PyTest's output, filtering (-k) and plugins:

    pytest -m regression -v
    pytest -m regression -k order
"""

from pathlib import Path

import pytest

from regression_framework.config_loader import load_config
from regression_framework.discovery import discover_tests
from regression_framework.runner import RunOptions, run_single_test

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = load_config(PROJECT_ROOT / "config" / "config.yaml")
TEST_CASES = discover_tests(PROJECT_ROOT / CONFIG["test_dir"], CONFIG["default_timeout"], CONFIG["tags"])
OPTIONS = RunOptions(retries=CONFIG["retries"], cwd=PROJECT_ROOT)


@pytest.mark.regression
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda test: test.name)
def test_regression_case(test_case):
    if test_case.skip:
        pytest.skip(test_case.skip_reason)
    result = run_single_test(test_case, OPTIONS)
    assert result.passed, "\n".join(result.failures)
