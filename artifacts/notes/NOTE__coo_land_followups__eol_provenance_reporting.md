# coo land Policy Follow-ups

- Enforce repo-level EOL policy via `.gitattributes` plus a one-time mechanical normalization pass to prevent merge churn.
- Add a dedicated `coo land-by-path` command mode with explicit provenance gate defaults (`origin/main` baseline, allowlist hash check).
- Route all `REPORT_BLOCKED__*` outputs to active gitignored evidence directories by default so blocked flows never dirty tracked paths.
