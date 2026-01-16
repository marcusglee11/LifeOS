# Log Retention Policy

## Stewardship Runner Logs

Location: `logs/steward_runner/<run-id>.jsonl`

### Retention by Context

| Context | Location | Retention | Owner |
|---------|----------|-----------|-------|
| Local development | `logs/steward_runner/` | 30 days | Developer |
| CI pipeline | Build artifacts | 90 days | CI system |
| Governance audit | `archive/logs/` | Indefinite | Doc Steward |

### Cleanup Rules

1. **Local**: Logs older than 30 days may be deleted unless referenced by open issue
2. **CI**: Artifacts auto-expire per platform default (GitHub: 90 days)
3. **Pre-deletion check**: Before deleting logs related to governance decisions, export to `archive/logs/`

### Log Content

Each JSONL entry contains:
- `timestamp`: ISO 8601 UTC
- `run_id`: Unique run identifier
- `event`: Event type (preflight, test, validate, commit, etc.)
- Event-specific data (files, results, errors)

### Audit Trail

Logs are append-only during a run. The `run_id` ties all entries together.
For governance audits, the complete log for a run provides deterministic replay evidence.
