from regression_framework.history import HistoryStore, compare_with_previous
from regression_framework.models import RunReport, Status
from tests.conftest import make_result


def make_report(*results) -> RunReport:
    return RunReport(started_at="2026-01-01T10:00:00", wall_time=1.0, results=list(results))


def test_empty_history(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    assert store.last_run() is None
    assert store.recent_runs() == []


def test_save_and_read_runs(tmp_path):
    store = HistoryStore(tmp_path / "nested" / "history.db")  # folder is created automatically

    first = store.save_run(make_report(make_result("a"), make_result("b", Status.FAILED)))
    second = store.save_run(make_report(make_result("a")))

    assert (first, second) == (1, 2)
    assert store.last_run() == (2, {"a": "PASSED"})

    runs = store.recent_runs()
    assert [run["id"] for run in runs] == [1, 2]  # oldest first
    assert runs[0]["failed"] == 1
    assert [run["id"] for run in store.recent_runs(limit=1)] == [2]


def test_compare_with_no_previous_run():
    assert compare_with_previous(None, [make_result("a")]) is None


def test_compare_detects_every_kind_of_change():
    previous = (7, {"was_ok": "PASSED", "was_broken": "FAILED", "still_broken": "FAILED", "stable": "PASSED"})
    results = [
        make_result("was_ok", Status.FAILED),
        make_result("was_broken"),
        make_result("still_broken", Status.FAILED),
        make_result("stable"),
        make_result("brand_new"),
        make_result("skipped", Status.SKIPPED),
    ]

    comparison = compare_with_previous(previous, results)

    assert comparison.previous_run == 7
    assert comparison.new_failures == ["was_ok"]
    assert comparison.fixed == ["was_broken"]
    assert comparison.still_failing == ["still_broken"]
    assert comparison.new_tests == ["brand_new"]
    assert [r.change for r in results] == ["new_failure", "fixed", "still_failing", "", "new_test", ""]
