"""Health-check endpoint simulator - used to demo performance checks and flaky tests.

    python sample_app/health_service.py --latency 0.2

Environment variables:
    COLD_START=1  -> the first attempt fails with "service warming up" (a flaky
                     dependency); retries succeed. Uses REGRESS_ATTEMPT, which
                     the framework sets for every test run.
    DEMO_BUG=1    -> adds 1.5s of extra latency (a performance regression).
"""

import argparse
import json
import os
import sys
import time

VERSION = "2.4.1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Health-check service")
    parser.add_argument("--latency", type=float, default=0.05, help="simulated response time in seconds")
    args = parser.parse_args()

    if os.environ.get("COLD_START") and os.environ.get("REGRESS_ATTEMPT", "1") == "1":
        print("Error: service warming up, try again", file=sys.stderr)
        return 1

    latency = args.latency + (1.5 if os.environ.get("DEMO_BUG") else 0)
    time.sleep(latency)

    print(json.dumps({"status": "ok", "version": VERSION, "checks": {"database": "ok", "cache": "ok"}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
