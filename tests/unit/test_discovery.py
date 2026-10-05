import json

import pytest

from regression_framework.discovery import discover_tests, filter_by_name, filter_by_tags, find_suite_files
from regression_framework.models import TestCase


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_find_suite_files_only_picks_test_files(tmp_path):
    write_file(tmp_path / "test_a.yaml", "tests: []")
    write_file(tmp_path / "nested" / "test_b.json", '{"tests": []}')
    write_file(tmp_path / "notes.yaml", "tests: []")       # wrong prefix
    write_file(tmp_path / "test_readme.txt", "hello")      # wrong extension

    names = sorted(path.name for path in find_suite_files(tmp_path))

    assert names == ["test_a.yaml", "test_b.json"]


def test_find_suite_files_missing_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_suite_files(tmp_path / "missing")


def test_discover_tests_loads_yaml_and_json(tmp_path):
    write_file(tmp_path / "test_a.yaml", "tests:\n  - name: one\n    command: echo 1\n")
    write_file(tmp_path / "test_b.json", json.dumps({"tests": [{"name": "two", "command": "echo 2"}]}))

    tests = discover_tests(tmp_path, default_timeout=7)

    assert {test.name for test in tests} == {"one", "two"}
    assert all(test.timeout == 7 for test in tests)


def test_suite_defaults_are_applied(tmp_path):
    write_file(tmp_path / "test_a.yaml", (
        "defaults:\n  timeout: 3\n  tags: [orders]\n  command: echo shared\n"
        "tests:\n  - name: one\n    tags: [smoke]\n  - name: two\n    timeout: 9\n"
    ))
    one, two = discover_tests(tmp_path, default_timeout=30)

    assert (one.command, one.timeout, one.tags) == ("echo shared", 3, ["orders", "smoke"])
    assert two.timeout == 9


def test_discover_tests_rejects_duplicate_names(tmp_path):
    write_file(tmp_path / "test_a.yaml", "tests:\n  - {name: same, command: echo 1}\n  - {name: same, command: echo 2}")
    with pytest.raises(ValueError, match="Duplicate test name"):
        discover_tests(tmp_path)


@pytest.mark.parametrize("content, message", [
    ("tests:\n  - {name: t, command: echo, expected_ouput: x}\n", "unknown field"),
    ("tests:\n  - {name: t}\n", "command"),
    ("test:\n  - {name: t, command: echo}\n", "Unknown top-level"),
    ("tests: {name: t}\n", "must be a list"),
    ("defaults: [1]\ntests: []\n", "'defaults' must be"),
])
def test_bad_suite_files_are_reported(tmp_path, content, message):
    write_file(tmp_path / "test_a.yaml", content)
    with pytest.raises(ValueError, match=message):
        discover_tests(tmp_path)


def test_filter_by_tags():
    tests = [
        TestCase(name="a", command="echo", tags=["smoke"]),
        TestCase(name="b", command="echo", tags=["slow"]),
        TestCase(name="c", command="echo"),
    ]
    assert [t.name for t in filter_by_tags(tests, ["smoke"])] == ["a"]
    assert [t.name for t in filter_by_tags(tests, ["smoke", "slow"])] == ["a", "b"]
    assert len(filter_by_tags(tests, [])) == 3


def test_filter_by_name_is_case_insensitive():
    tests = [TestCase(name="order_quote", command="x"), TestCase(name="calculator_add", command="x")]
    assert [t.name for t in filter_by_name(tests, "ORDER")] == ["order_quote"]
    assert len(filter_by_name(tests, None)) == 2
