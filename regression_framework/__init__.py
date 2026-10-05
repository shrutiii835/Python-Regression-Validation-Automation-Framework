"""A config-driven regression testing framework.

Each module has one job:

    config_loader  -> reads settings from YAML / JSON files
    discovery      -> finds suite files and turns them into TestCase objects
    executor       -> runs a single command with subprocess
    validators     -> compares expected vs actual results (one function per check)
    runner         -> runs many tests in parallel, with retries
    history        -> stores runs in SQLite and detects new failures
    git_info       -> which commit/branch was tested
    reporters/     -> console, HTML, JSON, JUnit XML and Markdown output
    logger         -> one central place to configure logging
    cli            -> the `regress` command
"""

__version__ = "2.0.0"
