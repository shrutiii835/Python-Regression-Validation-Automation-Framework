"""Markdown summary - shown on the GitHub Actions run page, or pasted into a pull request."""

from pathlib import Path

from regression_framework.models import RunReport


def build_markdown(report: RunReport) -> str:
    summary = report.summary
    icon = "✅" if summary["failed"] == 0 else "❌"
    executed = summary["total"] - summary["skipped"]

    lines = [
        f"## {icon} Regression results: {summary['passed']}/{executed} passed",
        "",
        f"Branch `{report.git_branch}` · commit `{report.git_commit}` · {report.started_at}",
        "",
        "| Total | Passed | Failed | Flaky | Skipped | Pass rate | Duration |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        f"| {summary['total']} | {summary['passed']} | {summary['failed']} | {summary['flaky']} "
        f"| {summary['skipped']} | {summary['pass_rate']}% | {summary['wall_time']}s |",
        "",
    ]

    comparison = report.comparison
    if comparison and comparison.new_failures:
        lines.append(f"### 🔴 New failures since run #{comparison.previous_run}")
        lines += [f"- `{name}`" for name in comparison.new_failures] + [""]
    if comparison and comparison.fixed:
        lines.append(f"### 🟢 Fixed since run #{comparison.previous_run}")
        lines += [f"- `{name}`" for name in comparison.fixed] + [""]

    failed = [r for r in report.results if r.failed]
    if failed:
        lines.append("### Failed tests")
        for result in failed:
            lines += [
                "<details>",
                f"<summary><code>{result.name}</code></summary>",
                "",
                "```diff",
                f"$ {result.command}",
                *result.failures,
                "```",
                "</details>",
                "",
            ]

    flaky = [r.name for r in report.results if r.is_flaky]
    if flaky:
        lines.append("### 🟡 Flaky tests (passed after retry)")
        lines += [f"- `{name}`" for name in flaky] + [""]

    return "\n".join(lines)


def write_markdown_report(report: RunReport, report_dir: Path) -> Path:
    path = report_dir / "summary.md"
    path.write_text(build_markdown(report), encoding="utf-8")
    return path
