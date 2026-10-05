"""Run a single command using subprocess and capture what happened."""

import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    """Raw output of one command run."""

    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False


def build_command(command: str | list[str]) -> list[str]:
    """Turn the command into a list of arguments for subprocess.

    A leading "python"/"python3" is replaced with the current interpreter so
    tests use the same Python (and virtual environment) as the framework.
    """
    parts = shlex.split(command) if isinstance(command, str) else [str(part) for part in command]
    if parts and parts[0] in ("python", "python3"):
        parts[0] = sys.executable
    return parts


def command_to_string(command: str | list[str]) -> str:
    """A readable version of the command for reports."""
    return command if isinstance(command, str) else shlex.join(str(part) for part in command)


def run_command(
    command: str | list[str],
    timeout: float = 30,
    cwd: str | Path | None = None,
    stdin: str | None = None,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run the command and return its exit code, output and duration.

    This never raises for a failing command: problems such as timeouts or a
    missing program are reported in the returned CommandResult instead.
    """
    args = build_command(command)
    # Start from the current environment and add the test's own variables on top.
    full_env = {**os.environ, **{key: str(value) for key, value in (env or {}).items()}}
    start = time.perf_counter()

    try:
        completed = subprocess.run(
            args,
            input=stdin if stdin is not None else "",  # never wait for keyboard input
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=cwd,
            env=full_env,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(-1, "", f"Command timed out after {timeout} seconds",
                             time.perf_counter() - start, timed_out=True)
    except FileNotFoundError:
        return CommandResult(-1, "", f"Command not found: {args[0] if args else command!r}",
                             time.perf_counter() - start)
    except OSError as error:
        return CommandResult(-1, "", f"Could not start command: {error}", time.perf_counter() - start)

    return CommandResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration=time.perf_counter() - start,
    )
