# Shortcuts for common tasks. Run `make help` to see them all.
# (Windows users: run the commands on the right-hand side directly.)

.PHONY: help install lint test coverage regress smoke demo-bug report history clean

help:           ## Show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

install:        ## Install the framework and dev tools (editable)
	python -m pip install -e ".[dev]"

lint:           ## Check code style with ruff
	ruff check .

test:           ## Run the framework's own unit tests
	pytest tests/unit

coverage:       ## Unit tests with a coverage report (fails under 90%)
	pytest tests/unit --cov --cov-report=term --cov-fail-under=90

regress:        ## Run all regression suites
	regress run

smoke:          ## Run only tests tagged "smoke"
	regress run --tags smoke

demo-bug:       ## Run the suites against a version of the app with a bug in it
	DEMO_BUG=1 regress run

report:         ## Open the latest HTML report
	python -c "import webbrowser, pathlib; webbrowser.open(pathlib.Path('reports/report.html').resolve().as_uri())"

history:        ## Show recent runs
	regress history

clean:          ## Delete reports, logs, history and caches
	rm -rf reports logs .regress .pytest_cache .coverage
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
