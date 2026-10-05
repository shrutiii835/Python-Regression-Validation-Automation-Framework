"""Allows `python -m regression_framework run` as an alternative to `regress run`."""

import sys

from regression_framework.cli import main

sys.exit(main())
