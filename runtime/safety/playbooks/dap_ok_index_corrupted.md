# Playbook: DAP OK / INDEX Corrupted

## Symptoms
- INDEX file missing or invalid
- Health check `check_index_coherence` fails

## Recovery
1. Regenerate INDEX with `IndexUpdater.update()`
2. Verify coherence
3. Create AMU₀ snapshot
