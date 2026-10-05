"""Find test suite files and load the test cases inside them.

A suite file:
  * lives anywhere under the test directory (sub-folders are fine)
  * has a name starting with "test_" and ends in .yaml, .yml or .json
  * has a "tests" list, and optionally a "defaults" block shared by every test
"""

from pathlib import Path

from regression_framework.config_loader import read_data_file
from regression_framework.logger import get_logger
from regression_framework.models import TestCase

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = (".yaml", ".yml", ".json")
SUITE_KEYS = {"defaults", "tests"}


def find_suite_files(test_dir: str | Path) -> list[Path]:
    """Return all suite files under test_dir, sorted so runs are repeatable."""
    test_dir = Path(test_dir)
    if not test_dir.is_dir():
        raise FileNotFoundError(f"Test directory not found: {test_dir}")

    files = [
        path for path in test_dir.rglob("test_*")
        if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS
    ]
    return sorted(files)


def load_suite_file(path: str | Path, default_timeout: float = 30) -> list[TestCase]:
    """Load every test case from one suite file."""
    data = read_data_file(path)

    unknown = set(data) - SUITE_KEYS
    if unknown:
        raise ValueError(f"Unknown top-level key(s) {sorted(unknown)} in {path} (allowed: defaults, tests)")

    suite_defaults = data.get("defaults", {})
    raw_tests = data.get("tests", [])
    if not isinstance(suite_defaults, dict):
        raise ValueError(f"'defaults' must be a mapping/object in {path}")
    if not isinstance(raw_tests, list):
        raise ValueError(f"'tests' must be a list in {path}")

    defaults = {"timeout": default_timeout, **suite_defaults}
    return [TestCase.from_dict(item, defaults, Path(path).as_posix()) for item in raw_tests]


def filter_by_tags(test_cases: list[TestCase], tags: list[str] | None) -> list[TestCase]:
    """Keep tests that have at least one of the given tags. No tags = keep everything."""
    if not tags:
        return test_cases
    wanted = set(tags)
    return [test for test in test_cases if wanted & set(test.tags)]


def filter_by_name(test_cases: list[TestCase], text: str | None) -> list[TestCase]:
    """Keep tests whose name contains `text` (case-insensitive)."""
    if not text:
        return test_cases
    return [test for test in test_cases if text.lower() in test.name.lower()]


def check_unique_names(test_cases: list[TestCase]) -> None:
    """Test names are used as IDs in reports and history, so they must be unique."""
    seen: dict[str, str] = {}
    for test in test_cases:
        if test.name in seen:
            raise ValueError(
                f"Duplicate test name '{test.name}' in {test.source_file} "
                f"(already defined in {seen[test.name]})"
            )
        seen[test.name] = test.source_file


def discover_tests(
    test_dir: str | Path,
    default_timeout: float = 30,
    tags: list[str] | None = None,
    name_filter: str | None = None,
) -> list[TestCase]:
    """Find, load and filter all test cases under test_dir."""
    all_tests: list[TestCase] = []
    for suite_file in find_suite_files(test_dir):
        suite_tests = load_suite_file(suite_file, default_timeout)
        logger.debug("Loaded %d test(s) from %s", len(suite_tests), suite_file)
        all_tests.extend(suite_tests)

    check_unique_names(all_tests)

    selected = filter_by_name(filter_by_tags(all_tests, tags), name_filter)
    logger.info("Discovered %d test(s), %d selected", len(all_tests), len(selected))
    return selected
