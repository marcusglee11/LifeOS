# SCHEMA — Acceptance & Closure v1.0

**Version**: 1.0
**Status**: Canonical
**Validator**: `runtime/tools/coo_acceptance_policy.py`

---

## Purpose

This schema defines the structure of acceptance notes used to formally close
work items in LifeOS.  Acceptance notes record evidence that a change was
landed cleanly, with verified proofs, and are machine-parseable by
`coo_acceptance_policy.py`.

## File Naming Convention

```
artifacts/acceptance/ACCEPTED__<slug>__v<semver>.md
```

- `<slug>`: descriptive, underscore-separated identifier (e.g., `coo_land__gates_provenance_scope_eol_reporting`)
- `<semver>`: optional version (e.g., `v1.0`).  Omit if not applicable.

Example: `ACCEPTED__OpenClaw_FrontOffice_Receipt_P0__RESULT_PRETTY_ERR_BYTES.md`

## Required Fields

Each acceptance note MUST contain exactly one occurrence of each required key.
Keys are specified as `KEY=value` on a single line.

| Key | Format | Description |
|-----|--------|-------------|
| `TITLE` | free text | Human-readable title of the accepted work |
| `SCOPE` | free text | What was accepted (brief) |
| `MAIN_HEAD` | 40-char hex SHA | Git HEAD on main after merge |
| `SOURCE_REFS` | comma-separated SHAs or refs | Source commits/branches |
| `EVID_DIR` | relative path | Evidence directory path |
| `RECEIPTS` | comma-separated filenames | Receipt files produced |
| `VERIFICATIONS` | free text | Commands run + return codes |
| `CLEAN_PROOF_PRE` | status string | Repo status before operation (must indicate clean) |
| `CLEAN_PROOF_POST` | status string | Repo status after operation (must indicate clean) |

## Optional Fields

| Key | Format | Description |
|-----|--------|-------------|
| `DEVIATIONS` | free text | Deviations from expected process |
| `FOLLOWUPS` | free text | Follow-up work items |

## Clean Proof Rules (MANDATORY)

> **Fail-closed**: If clean proofs are missing or indicate a non-clean state,
> the acceptance note is INVALID and closure MUST NOT proceed.

- `CLEAN_PROOF_PRE` and `CLEAN_PROOF_POST` MUST be present.
- Their values MUST contain one of: `clean`, `empty`, `0 files`, `0 files modified`.
- Any other value is treated as a dirty proof and causes validation failure.

## Validation Rules

1. All required keys present exactly once.
2. No unknown keys.
3. `MAIN_HEAD` is a valid 40-character hex string.
4. `EVID_DIR` is non-empty.
5. Clean proofs comply with clean proof rules above.

## Deterministic Ordering

- Keys SHOULD appear in the order listed above.
- Lists (SOURCE_REFS, RECEIPTS) SHOULD be lexicographically sorted.
- No timestamps in the note body unless required by a specific field.

## Blocked Reports

If an acceptance/closure action cannot proceed:

1. Write a blocked report to the EVID dir (gitignored), NOT to tracked repo paths.
2. Filename: `REPORT_BLOCKED__<slug>__<timestamp>.md`
3. Include: the exact missing artifact/problem, commands run + outputs, repo status/diff.

## Validator Usage

```bash
# Validate an acceptance note
python -m runtime.tools.coo_acceptance_policy validate path/to/note.md

# Generate a skeleton
python -m runtime.tools.coo_acceptance_policy skeleton
```

## Config-Aware Clean Invariant

Before generating clean proofs, agents MUST verify EOL config compliance:

```bash
python -m runtime.tools.coo_land_policy clean-check --repo .
```

This checks:

1. `core.autocrlf` is `false` (not `true` or `input`)
2. Working tree has zero modifications
3. If dirty, classifies as `EOL_CHURN` vs `CONTENT_DIRTY`

Use `--auto-fix` to automatically set `core.autocrlf=false` locally.
