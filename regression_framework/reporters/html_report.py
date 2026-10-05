"""Self-contained HTML dashboard, rendered from a Jinja2 template."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from regression_framework import __version__
from regression_framework.models import RunReport

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# Show the most important results first.
STATUS_ORDER = {"FAILED": 0, "FLAKY": 1, "PASSED": 2, "SKIPPED": 3}


def diff_line_class(line: str) -> str:
    """CSS class used to colour lines of a diff."""
    if line.startswith(("+++", "---")):
        return "diff-meta"
    if line.startswith("+"):
        return "diff-add"
    if line.startswith("-"):
        return "diff-del"
    if line.startswith("@@"):
        return "diff-hunk"
    return ""


def render_html(report: RunReport) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    env.filters["diff_class"] = diff_line_class
    template = env.get_template("report.html.j2")

    data = report.to_dict()
    data["results"].sort(key=lambda result: STATUS_ORDER[result["display_status"]])
    return template.render(report=data, version=__version__)


def write_html_report(report: RunReport, report_dir: Path) -> Path:
    path = report_dir / "report.html"
    path.write_text(render_html(report), encoding="utf-8")
    return path
