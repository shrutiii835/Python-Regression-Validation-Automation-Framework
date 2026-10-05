import json

import pytest

from regression_framework.config_loader import DEFAULT_CONFIG, load_config, read_data_file


def test_load_config_without_file_returns_defaults():
    assert load_config() == DEFAULT_CONFIG


def test_load_yaml_config_overrides_defaults(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("workers: 8\nretries: 3\n")

    config = load_config(config_file)

    assert config["workers"] == 8
    assert config["retries"] == 3
    assert config["report_dir"] == DEFAULT_CONFIG["report_dir"]  # untouched default


def test_load_json_config(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"default_timeout": 5}))

    assert load_config(config_file)["default_timeout"] == 5


def test_empty_yaml_file_gives_defaults(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")
    assert load_config(config_file) == DEFAULT_CONFIG


def test_missing_file_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_data_file(tmp_path / "missing.yaml")


def test_unsupported_extension_raises_error(tmp_path):
    bad_file = tmp_path / "config.txt"
    bad_file.write_text("workers: 2")
    with pytest.raises(ValueError, match="Unsupported file type"):
        read_data_file(bad_file)


def test_top_level_must_be_a_mapping(tmp_path):
    bad_file = tmp_path / "config.yaml"
    bad_file.write_text("- a\n- b\n")
    with pytest.raises(ValueError, match="mapping"):
        read_data_file(bad_file)


@pytest.mark.parametrize(
    "content, message",
    [
        ("workers: 0", "workers"),
        ("retries: -1", "retries"),
        ("retry_delay: -1", "retry_delay"),
        ("default_timeout: 0", "default_timeout"),
        ("tags: smoke", "tags"),
        ("log_level: LOUD", "log_level"),
        ("wrokers: 2", "Unknown config setting"),
    ],
)
def test_invalid_config_values_are_rejected(tmp_path, content, message):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(content)
    with pytest.raises(ValueError, match=message):
        load_config(config_file)
