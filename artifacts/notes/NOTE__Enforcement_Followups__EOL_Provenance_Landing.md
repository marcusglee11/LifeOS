# NOTE — Enforcement Follow-ups: EOL + Provenance Landing

1. Enforce repo-level EOL policy via `.gitattributes` + one-time mechanical normalization (prevent dirty merges).
2. Add `coo` "land-by-path" command and provenance gate (base on `origin/main`; expected-path allowlist).
3. Default all `REPORT_BLOCKED` outputs to gitignored evidence dir (never dirty `main`).
