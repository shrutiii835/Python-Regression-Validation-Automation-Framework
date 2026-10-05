"""Load framework settings from a YAML or JSON file."""

import json
from pathlib import Path

import yaml

# Used for any setting that is not present in the config file.
DEFAULT_CONFIG = {
    "test_dir": "test_suites",
    "report_dir": "reports",
    "log_dir": "logs",
    "log_level": "WARNING",      # console verbosity; the log file always gets everything
    "workers": 4,
    "retries": 1,
    "retry_delay": 0.0,           # seconds to wait before retrying
    "default_timeout": 30,
    "tags": [],
    "history_db": ".regress/history.db",
}


def read_data_file(path: str | Path) -> dict:
    """Read a .yaml, .yml or .json file and return its contents as a dict."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, encoding="utf-8") as file:
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(file)
        elif path.suffix == ".json":
            data = json.load(file)
        else:
            raise ValueError(f"Unsupported file type '{path.suffix}' (use .yaml, .yml or .json)")

    if data is None:  # an empty YAML file
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Top level of {path} must be a mapping/object")
    return data


def load_config(path: str | Path | None = None) -> dict:
    """Return the defaults, updated with any values found in the config file."""
    config = dict(DEFAULT_CONFIG)
    if path is not None:
        config.update(read_data_file(path))
    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    """Fail early with a clear message if a setting has an invalid value."""
    unknown = set(config) - set(DEFAULT_CONFIG)
    if unknown:
        raise ValueError(f"Unknown config setting(s): {sorted(unknown)}")
    if not isinstance(config["workers"], int) or config["workers"] < 1:
        raise ValueError("'workers' must be a whole number >= 1")
    if not isinstance(config["retries"], int) or config["retries"] < 0:
        raise ValueError("'retries' must be a whole number >= 0")
    if not isinstance(config["retry_delay"], (int, float)) or config["retry_delay"] < 0:
        raise ValueError("'retry_delay' must be a number >= 0")
    if not isinstance(config["default_timeout"], (int, float)) or config["default_timeout"] <= 0:
        raise ValueError("'default_timeout' must be a number > 0")
    if not isinstance(config["tags"], list):
        raise ValueError("'tags' must be a list")
    if config["log_level"].upper() not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        raise ValueError("'log_level' must be DEBUG, INFO, WARNING or ERROR")
