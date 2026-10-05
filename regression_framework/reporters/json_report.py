"""Machine-readable JSON report (handy for dashboards or other tools)."""

import json
from pathlib import Path

from regression_framework.models import RunReport


def write_json_report(report: RunReport, report_dir: Path) -> Path:
    path = report_dir / "results.json"
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path
