import pytest

from regression_framework.models import Status, TestCase
from tests.conftest import make_result


def test_from_dict_applies_defaults_and_combines_tags():
    test = TestCase.from_dict(
        {"name": "t", "command": "echo", "tags": ["smoke"]},
        defaults={"timeout": 5, "tags": ["orders"], "retries": 3},
    )
    assert test.timeout == 5
    assert test.retries == 3
    assert test.tags == ["orders", "smoke"]


def test_test_values_override_defaults():
    test = TestCase.from_dict({"name": "t", "command": "echo", "timeout": 1}, defaults={"timeout": 5})
    assert test.timeout == 1


def test_command_can_come_from_defaults():
    test = TestCase.from_dict({"name": "t"}, defaults={"command": "echo hi"})
    assert test.command == "echo hi"


@pytest.mark.parametrize("data, message", [
    ({"command": "echo"}, "name"),
    ({"name": "t"}, "command"),
    ({"name": "t", "command": "echo", "expected_ouput": "x"}, "unknown field"),
    ("not a dict", "mapping"),
])
def test_from_dict_rejects_bad_input(data, message):
    with pytest.raises(ValueError, match=message):
        TestCase.from_dict(data)


def test_skip_reason():
    assert TestCase(name="t", command="x", skip="later").skip_reason == "later"
    assert TestCase(name="t", command="x", skip=True).skip_reason == "marked as skip"
    assert TestCase(name="t", command="x").skip_reason == ""


def test_result_status_helpers():
    assert make_result(attempts=2).is_flaky
    assert make_result(attempts=2).display_status == "FLAKY"
    assert not make_result(status=Status.FAILED, attempts=2).is_flaky
    assert make_result(status=Status.FAILED).to_dict()["status"] == "FAILED"


def test_report_summary(sample_report):
    summary = sample_report.summary
    assert summary["total"] == 4
    assert summary["passed"] == 2
    assert summary["failed"] == 1
    assert summary["skipped"] == 1
    assert summary["flaky"] == 1
    assert summary["pass_rate"] == 66.7       # 2 of 3 executed tests
    assert summary["test_time"] == 1.5
    assert summary["speedup"] == 1.5
