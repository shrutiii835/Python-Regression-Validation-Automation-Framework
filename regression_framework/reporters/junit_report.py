"""JUnit XML report - the standard test result format understood by
GitHub Actions, GitLab, Jenkins, Azure DevOps and most other CI tools."""

import xml.etree.ElementTree as ET
from pathlib import Path

from regression_framework.models import RunReport, Status


def suite_class_name(source_file: str) -> str:
    """'test_suites/orders/test_orders.yaml' -> 'test_suites.orders.test_orders'"""
    return Path(source_file).with_suffix("").as_posix().replace("/", ".") or "regression"


def write_junit_report(report: RunReport, report_dir: Path) -> Path:
    summary = report.summary
    suite = ET.Element(
        "testsuite",
        name="regression",
        tests=str(summary["total"]),
        failures=str(summary["failed"]),
        skipped=str(summary["skipped"]),
        errors="0",
        time=f"{summary['wall_time']:.3f}",
        timestamp=report.started_at,
    )

    for result in report.results:
        case = ET.SubElement(
            suite, "testcase",
            name=result.name,
            classname=suite_class_name(result.source_file),
            time=f"{result.duration:.3f}",
        )
        if result.status == Status.FAILED:
            failure = ET.SubElement(case, "failure", message=result.failures[0].splitlines()[0])
            failure.text = "\n\n".join(result.failures)
        elif result.status == Status.SKIPPED:
            ET.SubElement(case, "skipped", message=result.skip_reason)
        if result.stdout:
            ET.SubElement(case, "system-out").text = result.stdout
        if result.stderr:
            ET.SubElement(case, "system-err").text = result.stderr

    tree = ET.ElementTree(suite)
    ET.indent(tree)
    path = report_dir / "junit.xml"
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path
