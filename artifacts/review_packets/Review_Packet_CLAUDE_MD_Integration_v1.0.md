# Review Packet: CLAUDE.md Integration

**Mode**: Lightweight Stewardship
**Date**: 2026-01-08
**Files Changed**: 3

## Summary
Integrated `CLAUDE.md` into the repository documentation structure. Added references in `README.md` and `docs/INDEX.md`, and regenerated the Strategic Corpus.

## Changes

| File | Change Type |
|------|-------------|
| [README.md](file:///c:/Users/cabra/Projects/LifeOS/README.md) | MODIFIED |
| [docs/INDEX.md](file:///c:/Users/cabra/Projects/LifeOS/docs/INDEX.md) | MODIFIED |
| [docs/LifeOS_Strategic_Corpus.md](file:///c:/Users/cabra/Projects/LifeOS/docs/LifeOS_Strategic_Corpus.md) | MODIFIED |

## Diff Appendix

### README.md
```diff
--- a/README.md
+++ b/README.md
@@ -14,6 +14,7 @@
 - `runtime/`: The LifeOS COO Runtime implementation (Python).
 - `scripts/`: Utility scripts for maintenance, stewardship, and usage.
 - `artifacts/`: Agent-generated artifacts (plans, packets, evidence).
+- `CLAUDE.md`: Claude Code agent guidance file.
 - `tests/`: Project-level tests.
```

### docs/INDEX.md
```diff
--- a/docs/INDEX.md
+++ b/docs/INDEX.md
@@ -1,4 +1,4 @@
-# LifeOS Documentation Index — Last Updated: 2026-01-07T23:57+11:00
+# LifeOS Documentation Index — Last Updated: 2026-01-08T10:55+11:00
 **Authority**: [LifeOS Constitution v2.0](./00_foundations/LifeOS_Constitution_v2.0.md)
 
 ---
@@ -24,6 +24,16 @@
 
 ---
 
+## Agent Guidance (Root Level)
+
+| File | Purpose |
+|------|---------|
+| [CLAUDE.md](../CLAUDE.md) | Claude Code (claude.ai/code) agent guidance |
+| [AGENTS.md](../AGENTS.md) | OpenCode agent instructions (Doc Steward subset) |
+| [GEMINI.md](../GEMINI.md) | Gemini agent constitution |
+
+---
+
 ## 00_admin — Project Admin (Thin Control Plane)
```

### docs/LifeOS_Strategic_Corpus.md
(Regenerated via script to include updated index references)
