"""End-to-end tests for the `regress` command, using small temporary suites."""

import json

import pytest

from regression_framework.cli import main


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A temporary project folder with a config file. Returns a helper to write suites."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps({
        "test_dir": "suites", "report_dir": "reports", "log_dir": "logs",
        "workers": 2, "retries": 0, "history_db": "history.db",
    }))

    def write_suite(tests):
        (tmp_path / "suites").mkdir(exist_ok=True)
        (tmp_path / "suites" / "test_suite.json").write_text(json.dumps({"tests": tests}))

    return write_suite


def echo_test(name, value, expected, tags=()):
    return {"name": name, "command": f"python -c \"print({value})\"", "expected_output": expected, "tags": list(tags)}


def run(*extra):
    return main(["run", "--config", "config.json", *extra])


def test_run_returns_0_and_writes_reports_when_all_pass(project, tmp_path):
    project([echo_test("ok", 1, "1")])

    assert run() == 0
    for name in ["report.html", "results.json", "junit.xml", "summary.md"]:
        assert (tmp_path / "reports" / name).is_file()
    assert (tmp_path / "logs" / "regression.log").is_file()


def test_run_returns_1_when_a_test_fails(project):
    project([echo_test("bad", 1, "2")])
    assert run() == 1


def test_run_detects_new_failure_compared_with_previous_run(project, tmp_path):
    project([echo_test("calc", 1, "1")])
    assert run() == 0

    project([echo_test("calc", 1, "999")])  # simulate a bug introduced by a code change
    assert run() == 1

    report = json.loads((tmp_path / "reports" / "results.json").read_text())
    assert report["run_number"] == 2
    assert report["comparison"]["new_failures"] == ["calc"]


def test_run_with_tags_and_name_filter(project):
    project([
        echo_test("order_fast", 1, "1", tags=["smoke"]),
        echo_test("order_broken", 1, "2", tags=["slow"]),
        echo_test("calc_broken", 1, "2", tags=["smoke"]),
    ])
    assert run("--tags", "smoke", "-k", "order") == 0


def test_run_with_no_matching_tests(project):
    project([echo_test("ok", 1, "1")])
    assert run("-k", "nothing_matches") == 1


def test_run_without_history(project, tmp_path):
    project([echo_test("ok", 1, "1")])
    assert run("--no-history", "--workers", "1", "--retries", "0", "-v") == 0
    assert not (tmp_path / "history.db").exists()


def test_list_command(project, capsys):
    project([echo_test("first", 1, "1"), {"name": "later", "command": "x", "skip": "not ready"}])

    assert main(["list", "--config", "config.json"]) == 0
    output = capsys.readouterr().out
    assert "first" in output and "[skip: not ready]" in output and "2 test(s)" in output


def test_history_command(project, capsys):
    project([echo_test("ok", 1, "1")])
    main(["history", "--config", "config.json"])
    assert "No runs recorded yet" in capsys.readouterr().out

    run()
    assert main(["history", "--config", "config.json"]) == 0
    assert "100.0%" in capsys.readouterr().out


def test_setup_errors_return_2(project, tmp_path):
    assert main(["run", "--config", "missing.yaml"]) == 2
    assert run("--workers", "0") == 2
    assert run("--test-dir", str(tmp_path / "missing")) == 2
