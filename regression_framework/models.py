"""Data classes shared across the framework.

TestCase   -> WHAT to run and WHAT we expect (loaded from a suite file)
TestResult -> WHAT actually happened when one test ran
Comparison -> how this run differs from the previous run
RunReport  -> everything about one complete run (used by every reporter)
"""

from dataclasses import asdict, dataclass, field, fields
from enum import Enum


class Status(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class TestCase:
    """One regression test."""

    # Tell PyTest this is not a test class (its name starts with "Test").
    __test__ = False

    name: str
    command: str | list[str]
    description: str = ""
    tags: list[str] = field(default_factory=list)

    # How to run it
    stdin: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    timeout: float = 30
    retries: int | None = None  # None = use the value from the config
    skip: bool | str = False    # True, or a string explaining why

    # What we expect
    expected_exit_code: int = 0
    expected_output: str | None = None
    expected_output_contains: list[str] = field(default_factory=list)
    expected_output_regex: str | None = None
    expected_json: dict | list | None = None
    expected_stderr_contains: list[str] = field(default_factory=list)
    expected_output_file: str | None = None  # "golden" snapshot file
    max_duration: float | None = None        # performance budget in seconds

    source_file: str = ""

    @classmethod
    def from_dict(cls, data: dict, defaults: dict | None = None, source_file: str = "") -> "TestCase":
        """Build a TestCase from a suite entry, filling gaps from the suite defaults."""
        if not isinstance(data, dict):
            raise ValueError(f"Each test must be a mapping/object (in {source_file})")
        defaults = defaults or {}

        values = {**defaults, **data}
        # Tags are combined (suite tags + test tags) instead of replaced.
        values["tags"] = list(dict.fromkeys([*defaults.get("tags", []), *data.get("tags", [])]))

        for required in ("name", "command"):
            if required not in values:
                raise ValueError(f"Test is missing required field '{required}' (in {source_file}): {data}")

        # Catch typos such as "expected_ouput" instead of silently ignoring them.
        allowed = {f.name for f in fields(cls)} - {"source_file"}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"Test '{values['name']}' has unknown field(s) {sorted(unknown)} (in {source_file})")

        values["source_file"] = source_file
        return cls(**values)

    @property
    def skip_reason(self) -> str:
        if isinstance(self.skip, str):
            return self.skip
        return "marked as skip" if self.skip else ""


@dataclass
class TestResult:
    """The outcome of running one TestCase (after any retries)."""

    __test__ = False

    name: str
    status: Status
    command: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    source_file: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    attempts: int = 0
    failures: list[str] = field(default_factory=list)
    skip_reason: str = ""
    change: str = ""  # compared with the previous run: "new_failure", "fixed", ...

    @property
    def passed(self) -> bool:
        return self.status == Status.PASSED

    @property
    def failed(self) -> bool:
        return self.status == Status.FAILED

    @property
    def is_flaky(self) -> bool:
        """A test is 'flaky' if it only passed after one or more retries."""
        return self.passed and self.attempts > 1

    @property
    def display_status(self) -> str:
        return "FLAKY" if self.is_flaky else self.status.value

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["display_status"] = self.display_status
        data["is_flaky"] = self.is_flaky
        return data


@dataclass
class Comparison:
    """Differences between this run and the previous run."""

    previous_run: int
    new_failures: list[str] = field(default_factory=list)  # passed before, failing now (regressions!)
    fixed: list[str] = field(default_factory=list)          # failed before, passing now
    still_failing: list[str] = field(default_factory=list)
    new_tests: list[str] = field(default_factory=list)


@dataclass
class RunReport:
    """Everything about one complete run."""

    started_at: str
    wall_time: float
    results: list[TestResult]
    workers: int = 1
    git_commit: str = "unknown"
    git_branch: str = "unknown"
    run_number: int | None = None
    comparison: Comparison | None = None
    trend: list[dict] = field(default_factory=list)  # recent runs, oldest first

    @property
    def summary(self) -> dict:
        executed = [r for r in self.results if r.status != Status.SKIPPED]
        passed = sum(1 for r in self.results if r.passed)
        test_time = sum(r.duration for r in self.results)
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": sum(1 for r in self.results if r.failed),
            "skipped": len(self.results) - len(executed),
            "flaky": sum(1 for r in self.results if r.is_flaky),
            "pass_rate": round(passed / len(executed) * 100, 1) if executed else 0.0,
            "wall_time": round(self.wall_time, 3),
            "test_time": round(test_time, 3),
            # How much faster the run was thanks to parallel workers.
            "speedup": round(test_time / self.wall_time, 1) if self.wall_time > 0 else 1.0,
        }

    def to_dict(self) -> dict:
        return {
            "run_number": self.run_number,
            "started_at": self.started_at,
            "workers": self.workers,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "summary": self.summary,
            "comparison": asdict(self.comparison) if self.comparison else None,
            "trend": self.trend,
            "results": [result.to_dict() for result in self.results],
        }
