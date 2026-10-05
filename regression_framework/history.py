"""Store every run in a small SQLite database to track trends and spot regressions.

Two tables:
    runs    -> one row per run (totals, git commit, timing)
    results -> one row per test per run (status, duration, attempts)
"""

import sqlite3
from contextlib import closing
from pathlib import Path

from regression_framework.models import Comparison, RunReport, Status, TestResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    git_commit  TEXT,
    git_branch  TEXT,
    total       INTEGER,
    passed      INTEGER,
    failed      INTEGER,
    skipped     INTEGER,
    flaky       INTEGER,
    pass_rate   REAL,
    wall_time   REAL
);
CREATE TABLE IF NOT EXISTS results (
    run_id      INTEGER NOT NULL REFERENCES runs(id),
    test_name   TEXT NOT NULL,
    status      TEXT NOT NULL,
    duration    REAL,
    attempts    INTEGER,
    PRIMARY KEY (run_id, test_name)
);
"""


class HistoryStore:
    """Read and write run history in a SQLite file."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # rows behave like dictionaries
        return conn

    def save_run(self, report: RunReport) -> int:
        """Save the run and its results. Returns the new run number."""
        summary = report.summary
        with closing(self._connect()) as conn, conn:  # second "conn" = commit on success
            cursor = conn.execute(
                "INSERT INTO runs (started_at, git_commit, git_branch, total, passed, failed, "
                "skipped, flaky, pass_rate, wall_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (report.started_at, report.git_commit, report.git_branch, summary["total"],
                 summary["passed"], summary["failed"], summary["skipped"], summary["flaky"],
                 summary["pass_rate"], summary["wall_time"]),
            )
            run_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO results (run_id, test_name, status, duration, attempts) VALUES (?, ?, ?, ?, ?)",
                [(run_id, r.name, r.status.value, r.duration, r.attempts) for r in report.results],
            )
        return run_id

    def last_run(self) -> tuple[int, dict[str, str]] | None:
        """Return (run number, {test name: status}) for the most recent run, or None."""
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
            if row is None:
                return None
            rows = conn.execute("SELECT test_name, status FROM results WHERE run_id = ?", (row["id"],))
            return row["id"], {r["test_name"]: r["status"] for r in rows}

    def recent_runs(self, limit: int = 20) -> list[dict]:
        """Return the most recent runs, oldest first (handy for trend charts)."""
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in reversed(rows)]


def compare_with_previous(previous: tuple[int, dict[str, str]] | None, results: list[TestResult]) -> Comparison | None:
    """Label each result as a new failure, fix, etc. compared with the previous run."""
    if previous is None:
        return None

    previous_run, previous_statuses = previous
    comparison = Comparison(previous_run=previous_run)

    for result in results:
        before = previous_statuses.get(result.name)
        if result.status == Status.SKIPPED:
            continue
        if before is None:
            result.change = "new_test"
            comparison.new_tests.append(result.name)
        elif result.failed and before == Status.PASSED.value:
            result.change = "new_failure"
            comparison.new_failures.append(result.name)
        elif result.passed and before == Status.FAILED.value:
            result.change = "fixed"
            comparison.fixed.append(result.name)
        elif result.failed and before == Status.FAILED.value:
            result.change = "still_failing"
            comparison.still_failing.append(result.name)

    return comparison
