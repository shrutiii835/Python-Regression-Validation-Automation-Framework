# Interview Demo Script (about 5 minutes)

A step-by-step walkthrough that shows every major feature. Run it from the project root
with the virtual environment active. Start from a clean state:

```bash
make clean          # or: rm -rf reports logs .regress
```

---

### 1. Show how a test is written (30 seconds)

Open `test_suites/orders/test_orders.yaml`.

> "Tests are plain YAML or JSON. Anyone can add one without writing Python. Each test is a command,
> some input, and what we expect back: an exit code, exact text, JSON fields, a regex, a time
> budget, or a golden file."

### 2. A healthy run (1 minute)

```bash
regress run
```

Point out:
- **Live progress** while 4 workers run in parallel, and the reported speed-up
- **FLAKY**: `health_after_cold_start` failed once, then passed on retry. It's flagged, not hidden.
- **SKIP** with a reason
- The four report files and the log file at the bottom

### 3. Introduce a bug (1.5 minutes)

> "Now imagine a developer refactors the pricing code and accidentally calculates tax
> *before* applying the discount. The app still runs and gives no error. Only the numbers are wrong."

```bash
DEMO_BUG=1 regress run          # Windows PowerShell: $env:DEMO_BUG=1; regress run
```

Point out:
- `$.tax: expected 6.48, got 7.2`: the JSON check names the **exact field** that changed
- The **snapshot diff** of the receipt, which looks just like `git diff`
- `Too slow: took 1.77s, limit is 1.00s`: a **performance regression**, not just a wrong value
- **"4 NEW FAILURES compared with run #1"**: history knows these used to pass
- Exit code is `1` (`echo $?`), which is what makes CI fail the build

### 4. Open the dashboard (1 minute)

```bash
make report         # or open reports/report.html
```

Show the **NEW FAILURE** badges, the **pass-rate trend chart**, the filter chips (*Failed*, *Flaky*),
search, and the coloured diff. Mention that it's a single self-contained HTML file, so it can be emailed
or uploaded as a CI artifact.

### 5. Fix it and show history (30 seconds)

```bash
regress run         # bug switched off again -> "4 fixed"
regress history
```

### 6. CI/CD (30 seconds)

Open `.github/workflows/regression.yml` (or the GitHub Actions tab):
lint → unit tests with a 90% coverage minimum on two Python versions → regression suites →
Markdown summary on the run page → reports uploaded as artifacts. It also runs nightly.

---

## Questions you might be asked

**Why threads instead of multiprocessing?**
Each worker starts a separate process and then just *waits* for it. Waiting releases Python's GIL,
so threads give real parallelism here with less overhead and simpler code.

**How do you handle flaky tests?**
Retries are configurable globally and per test. A test that passes only after a retry is reported
as FLAKY rather than PASSED, so the flakiness stays visible and can be fixed instead of hidden.

**How do you know a failure is new?**
Every run is stored in SQLite (run number, Git commit, and the status of each test). Each new run is
compared with the previous one, and every test is labelled *new failure*, *fixed* or *still failing*.

**What is snapshot / golden-file testing?**
The approved output is saved to a file once (`--update-snapshots`). Later runs must match it exactly,
and any difference is shown as a unified diff. It's ideal for reports, receipts and other long text.

**How would you add a new kind of check?**
Write a function `check_x(test, result) -> list[str]` in `validators.py`, add it to `CHECKS`, and add
the matching field to `TestCase`. The runner and reporters don't need to change.

**How does it integrate with CI?**
Exit codes (0, 1 or 2) gate the pipeline. JUnit XML is the standard format CI tools read. The Markdown
summary appears on the GitHub run page, and the HTML report is uploaded as an artifact.

**What would you add next?**
Running suites inside Docker containers for isolation, publishing the dashboard to GitHub Pages,
posting results as a PR comment, and a plugin system for custom reporters.
