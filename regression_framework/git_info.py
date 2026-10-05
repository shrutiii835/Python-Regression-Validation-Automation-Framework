"""Find out which Git commit and branch the tests are running against."""

import os
import subprocess


def _git(*args: str) -> str | None:
    try:
        completed = subprocess.run(["git", *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def get_git_info() -> dict[str, str]:
    """Return {"commit": ..., "branch": ...}, or "unknown" when not available."""
    commit = _git("rev-parse", "--short", "HEAD") or "unknown"

    # In GitHub Actions the checkout is often a "detached HEAD", so prefer its variables.
    branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME")
    if not branch:
        branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"

    return {"commit": commit, "branch": branch}
