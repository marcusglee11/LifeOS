# Playbook: AMU₀ Corruption

## Symptoms
- AMU₀ lineage unreadable or malformed
- Hash chain verification fails
- Health check `check_amu0_readability` fails

## Recovery
1. Identify last known good snapshot
2. Rollback using `rollback_to_snapshot()`
3. Verify chain integrity
4. Create fresh snapshot
