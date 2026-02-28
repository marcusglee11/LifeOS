---
description: Run full close-build lifecycle (tests, conditional doc stewardship, merge to main, cleanup) with deterministic report output.
---

Invoke the lifeos-workflow:close-build skill and follow it exactly as presented.

Default mode runs full close.
If user requests preflight only, run with `--dry-run`.
Primary command path: `python3 scripts/workflow/close_build.py`.
If blocked with `ISOLATION_REQUIRED`, run:
`python3 scripts/workflow/start_build.py --recover-primary`.
