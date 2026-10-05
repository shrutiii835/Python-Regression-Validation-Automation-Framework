import json
import xml.etree.ElementTree as ET

from regression_framework.models import Comparison, Status
from regression_framework.reporters import write_all_reports
from regression_framework.reporters.html_report import diff_line_class, render_html
from regression_framework.reporters.junit_report import suite_class_name
from regression_framework.reporters.markdown_report import build_markdown
from tests.conftest import make_result


def test_write_all_reports_creates_every_file(tmp_path, sample_report):
    paths = write_all_reports(sample_report, tmp_path / "reports")

    assert set(paths) == {"HTML", "JSON", "JUnit", "Markdown"}
    assert all(path.is_file() for path in paths.values())


def test_json_report(tmp_path, sample_report):
    data = json.loads(write_all_reports(sample_report, tmp_path)["JSON"].read_text())

    assert data["summary"]["failed"] == 1
    assert data["git_commit"] == "abc1234"
    assert [r["display_status"] for r in data["results"]] == ["PASSED", "FLAKY", "FAILED", "SKIPPED"]


def test_junit_report_is_valid_xml(tmp_path, sample_report):
    root = ET.parse(write_all_reports(sample_report, tmp_path)["JUnit"]).getroot()

    assert root.tag == "testsuite"
    assert root.get("tests") == "4"
    assert root.get("failures") == "1"
    assert root.get("skipped") == "1"
    broken = root.find("testcase[@name='broken_test']")
    assert broken.find("failure").get("message") == "Exit code: expected 0, got 1"
    assert broken.find("system-out").text == "out"
    assert root.find("testcase[@name='skipped_test']/skipped").get("message") == "not ready"


def test_suite_class_name():
    assert suite_class_name("test_suites/orders/test_orders.yaml") == "test_suites.orders.test_orders"


def test_markdown_lists_failures_and_changes(sample_report):
    sample_report.comparison = Comparison(previous_run=3, new_failures=["broken_test"], fixed=["ok_test"])
    text = build_markdown(sample_report)

    assert "❌ Regression results: 2/3 passed" in text
    assert "New failures since run #3" in text
    assert "Fixed since run #3" in text
    assert "<code>broken_test</code>" in text
    assert "Flaky tests" in text


def test_markdown_all_passed(sample_report):
    sample_report.results = [make_result("ok")]
    assert build_markdown(sample_report).startswith("## ✅")


def test_html_shows_failures_first_and_escapes_text(sample_report):
    sample_report.results.append(make_result("<script>alert(1)</script>", Status.FAILED))
    sample_report.trend = [{"id": 1, "pass_rate": 100.0, "failed": 0, "git_branch": "main", "git_commit": "a"},
                           {"id": 2, "pass_rate": 50.0, "failed": 1, "git_branch": "main", "git_commit": "b"}]
    page = render_html(sample_report)

    assert "&lt;script&gt;" in page
    assert "<script>alert(1)</script>" not in page
    assert page.index("broken_test") < page.index("ok_test")  # failed before passed
    assert "Pass rate trend" in page


def test_diff_line_class():
    assert diff_line_class("+added") == "diff-add"
    assert diff_line_class("-removed") == "diff-del"
    assert diff_line_class("--- file") == "diff-meta"
    assert diff_line_class("@@ -1 +1 @@") == "diff-hunk"
    assert diff_line_class(" same") == ""
