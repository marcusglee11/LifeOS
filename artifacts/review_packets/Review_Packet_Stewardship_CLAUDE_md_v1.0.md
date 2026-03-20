# Review Packet: Stewardship of CLAUDE.md

**Draft Date**: 2026-01-25
**Mission**: Stewardship of `CLAUDE.md`
**Author**: Antigravity (Gemini)

## 1. Scope Envelope

* **Allowed**: `docs/INDEX.md`, `docs/LifeOS_Strategic_Corpus.md`, `CLAUDE.md` (no changes needed), `docs/scripts/generate_strategic_context.py`.
* **Forbidden**: `docs/00_foundations/`, `docs/01_governance/`.

## 2. Summary

Formalized the stewardship of `CLAUDE.md`. Verified its content, updated `docs/INDEX.md` timestamp, and patched `docs/scripts/generate_strategic_context.py` to ensure `CLAUDE.md` is correctly included in the `LifeOS_Strategic_Corpus.md` despite being a root-level file. Re-generated the corpus to prove integration.

## 3. Issue Catalogue

| Priority | Issue | Status |
|----------|-------|--------|
| P1 | `CLAUDE.md` missing from Strategic Corpus | FIXED (Script patch) |
| P2 | `docs/INDEX.md` timestamp stale | FIXED |

## 4. Acceptance Criteria

| Criterion | Status | Evidence Pointer | SHA-256 |
|-----------|--------|------------------|---------|
| `CLAUDE.md` indexed in `docs/INDEX.md` | VERIFIED | `docs/INDEX.md` | `efabb3cbbb61b5a53b207761e88d9f41fc52d79e180529b494030287675e4e5c` |
| `CLAUDE.md` present in `LifeOS_Strategic_Corpus.md` | VERIFIED | `docs/LifeOS_Strategic_Corpus.md` (Line ~426) | `9e8856a020341264cc497505d65b2b59b571cd8f2eb470d2e88cb19334246bac` |
| Generation script handles root files | VERIFIED | `docs/scripts/generate_strategic_context.py` | `05ce6362244d169dd7e389f36a80a539b4a5d17fac1458ab8a8ce6ceac81be7a` |

## 5. Closure Evidence Checklist

| Category | Requirement | Verified |
|----------|-------------|----------|
| **Provenance** | Code commit hash + message | PENDING (User to commit) |
| | Docs commit hash + message | PENDING (User to commit) |
| | Changed file list (paths) | `docs/INDEX.md`, `docs/scripts/generate_strategic_context.py`, `docs/LifeOS_Strategic_Corpus.md` |
| **Artifacts** | `attempt_ledger.jsonl` | N/A |
| | `CEO_Terminal_Packet.md` | N/A |
| | `Review_Packet_attempt_XXXX.md` | N/A |
| | Closure Bundle + Validator Output | N/A |
| | Docs touched (each path) | See S4 |
| **Repro** | Test command(s) exact cmdline | `python docs/scripts/generate_strategic_context.py` |
| | Run command(s) to reproduce artifact | N/A |
| **Governance** | Doc-Steward routing proof | Included in Corpus |
| | Policy/Ruling refs invoked | N/A |
| **Outcome** | Terminal outcome proof | PASS |

## 6. Non-Goals

* Modifying `CLAUDE.md` content (it was deemed current).
* Moving `CLAUDE.md` to `docs/` (kept in root as per convention).

## 7. Appendix: Patch Set

### `docs/INDEX.md`

Updated timestamp to `2026-01-25T05:41:00Z`.

### `docs/scripts/generate_strategic_context.py`

Patched to include invalid `relative_to` paths (root files) and added `CLAUDE` to `PRIORITY_ORDER`.

```python
# Patch to include root files in processing list
    # [NEW] Include Root Agent Guidance
    claude_md = ROOT_DIR / "CLAUDE.md"
    if claude_md.exists():
        files_to_process.append(claude_md)

# Patch to Priority Order
        "AgentConstitution_GEMINI_Template",
        "CLAUDE",
    ]

# Patch to Sort Key Exception Handling
        try:
            rel_str = str(path.relative_to(DOCS_DIR))
        except ValueError:
            # Handle root files or files not in docs/
            return (99, path.name)
```
