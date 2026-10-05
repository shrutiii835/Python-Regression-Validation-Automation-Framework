from regression_framework.executor import CommandResult
from regression_framework.models import TestCase
from regression_framework.validators import json_mismatches, make_diff, validate


def make_command_result(exit_code=0, stdout="", stderr="", duration=0.1, timed_out=False):
    return CommandResult(exit_code=exit_code, stdout=stdout, stderr=stderr, duration=duration, timed_out=timed_out)


def check(stdout="", **expectations):
    """Validate a fake run that printed `stdout`, against the given expectations."""
    test = TestCase(name="t", command="x", **expectations)
    return validate(test, make_command_result(stdout=stdout))


# ---------------------------------------------------------------- basic checks

def test_passes_when_everything_matches():
    assert check("5\n", expected_output="5", expected_output_contains=["5"]) == []


def test_wrong_exit_code():
    failures = validate(TestCase(name="t", command="x"), make_command_result(exit_code=1))
    assert failures == ["Exit code: expected 0, got 1"]


def test_wrong_output():
    assert check("6", expected_output="5") == ["Output mismatch: expected '5', got '6'"]


def test_multiline_output_mismatch_shows_a_diff():
    failures = check("a\nB\nc", expected_output="a\nb\nc")
    assert "-b" in failures[0] and "+B" in failures[0]


def test_numbers_in_yaml_are_compared_as_text():
    # YAML turns `expected_output: 5` into the integer 5; it should still match "5".
    assert check("5", expected_output=5) == []


def test_output_contains_and_stderr_contains():
    test = TestCase(name="t", command="x", expected_output_contains=["hello", "missing"],
                    expected_stderr_contains=["warning"])
    failures = validate(test, make_command_result(stdout="hello world"))
    assert failures == ["Output does not contain 'missing'", "Stderr does not contain 'warning'"]


def test_regex():
    assert check("version 1.2.3", expected_output_regex=r"\d+\.\d+\.\d+") == []
    assert "does not match pattern" in check("version x", expected_output_regex=r"\d+")[0]


def test_timeout_is_a_failure():
    test = TestCase(name="t", command="x", timeout=3)
    assert validate(test, make_command_result(exit_code=-1, timed_out=True)) == ["Timed out after 3 seconds"]


def test_max_duration():
    test = TestCase(name="t", command="x", max_duration=1.0)
    assert validate(test, make_command_result(duration=0.5)) == []
    assert "Too slow" in validate(test, make_command_result(duration=1.5))[0]


# ---------------------------------------------------------------- JSON checks

def test_json_subset_match_allows_extra_keys():
    assert check('{"total": 10, "currency": "USD"}', expected_json={"total": 10}) == []


def test_json_invalid_output():
    assert check("not json", expected_json={"a": 1}) == ["Output is not valid JSON"]


def test_json_mismatches_report_exact_path():
    actual = {"order": {"items": [{"price": 5}], "total": 5}}
    expected = {"order": {"items": [{"price": 4}], "tax": 1}}
    assert json_mismatches(expected, actual) == [
        "$.order.items[0].price: expected 4, got 5",
        "$.order.tax: missing from output",
    ]


def test_json_type_and_length_mismatches():
    assert "expected an object" in json_mismatches({"a": 1}, [1])[0]
    assert "list of 2 item(s)" in json_mismatches([1, 2], [1])[0]
    assert json_mismatches([1, 2], [1, 2]) == []


# ---------------------------------------------------------------- snapshots

def test_snapshot_missing_file(tmp_path):
    test = TestCase(name="t", command="x", expected_output_file="snap.txt")
    failures = validate(test, make_command_result(stdout="hello"), base_dir=tmp_path)
    assert "Snapshot file not found" in failures[0]


def test_snapshot_update_then_compare(tmp_path):
    test = TestCase(name="t", command="x", expected_output_file="snaps/out.txt")

    assert validate(test, make_command_result(stdout="line 1\nline 2\n"), tmp_path, update_snapshots=True) == []
    assert (tmp_path / "snaps" / "out.txt").read_text() == "line 1\nline 2\n"

    assert validate(test, make_command_result(stdout="line 1\nline 2  \n\n"), tmp_path) == []  # whitespace ignored

    failures = validate(test, make_command_result(stdout="line 1\nline TWO\n"), tmp_path)
    assert "differs from snapshot" in failures[0]
    assert "-line 2" in failures[0] and "+line TWO" in failures[0]


def test_make_diff():
    diff = make_diff("a\nb", "a\nc")
    assert "-b" in diff and "+c" in diff
