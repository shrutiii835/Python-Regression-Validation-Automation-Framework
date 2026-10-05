"""Reporters turn a RunReport into files people and tools can read."""

from pathlib import Path

from regression_framework.models import RunReport
from regression_framework.reporters.html_report import write_html_report
from regression_framework.reporters.json_report import write_json_report
from regression_framework.reporters.junit_report import write_junit_report
from regression_framework.reporters.markdown_report import write_markdown_report


def write_all_reports(report: RunReport, report_dir: str | Path) -> dict[str, Path]:
    """Write every report format and return {format name: file path}."""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    return {
        "HTML": write_html_report(report, report_dir),
        "JSON": write_json_report(report, report_dir),
        "JUnit": write_junit_report(report, report_dir),
        "Markdown": write_markdown_report(report, report_dir),
    }
