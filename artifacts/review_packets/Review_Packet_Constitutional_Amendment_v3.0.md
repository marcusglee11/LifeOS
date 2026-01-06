# Review Packet: Constitutional Amendment - Lightweight Stewardship Mode

**Mode**: Standard Mission
**Date**: 2026-01-05
**Files Changed**: 4

## Summary

Amended `GEMINI.md` (now v3.0) to introduce **Lightweight Stewardship Mode** via Article XVIII, enabling a fast-path for routine operations that skips Plan Artefact gates and uses Diff-Based Context instead of full file flattening.

## Changes

| File | Change Type |
|------|-------------|
| `GEMINI.md` | MODIFIED |
| `docs/01_governance/AgentConstitution_GEMINI_Template_v1.0.md` | MODIFIED (sync copy) |
| `docs/INDEX.md` | MODIFIED (timestamp) |
| `docs/LifeOS_Strategic_Corpus.md` | REGENERATED |

## Key Additions

### Article XVIII — Lightweight Stewardship Mode

**Eligibility Criteria** (all must be true):
1. No governance-controlled paths modified
2. Total files modified ≤ 5
3. No new code logic (moves, renames, index updates only)
4. No council trigger conditions apply

**Gate Relaxations**:
- Plan Artefact: SKIPPED
- Full Flattening: REPLACED with Diff-Based Context
- Agent Packet Protocol: SKIPPED

**Diff-Based Context Rules**:
- NEW files ≤100 lines: Full content
- NEW files >100 lines: Outline + first 50 lines
- MODIFIED files: Unified diff with 10 lines context
- MOVED/RENAMED: Path change only
- DELETED: Path only

### Article III §6 — Tiered Flattening

Mission types now have explicit flattening requirements:
| Mission Type | Approach |
|-------------|----------|
| Lightweight Stewardship | Diff-Based Context |
| Standard Mission | Full for NEW, diff for MODIFIED |
| Council Review | Full flattening for ALL |

### Article XII — Carve-out

Added exception: Lightweight missions may use simplified Review Packet template.

## Diff Appendix

```diff
--- a/GEMINI.md
+++ b/GEMINI.md
@@ -178,6 +178,18 @@
 - Must propose remediation steps.
 - Must distinguish critical vs informational gaps.

+### 6. TIERED FLATTENING
+
+Flattening requirements vary by mission type:
+
+| Mission Type | Flattening Approach |
+|-------------|---------------------|
+| Lightweight Stewardship | Diff-Based Context (Art. XVIII §3) |
+| Standard Mission | Full flattening for NEW files; diff for MODIFIED |
+| Council Review | Full flattening for ALL touched files |
+
+Agent must declare mission type in Review Packet header.
+
 ---
@@ -426,8 +438,9 @@
    - Issue catalogue
    - Acceptance criteria with pass/fail status
    - Non-goals (explicit)
-   - **Appendix with flattened code** for ALL created/modified files
+   - **Appendix with flattened code** for ALL created/modified files (or Diff-Based Context for Lightweight missions)
 3. Verify the packet is valid per Appendix A Section 6 requirements
+4. **Exception**: Lightweight Stewardship missions (Art. XVIII) may use the simplified template

 ## Section 2. notify_user Gate
@@ -690,7 +703,78 @@

 ---

-# **End of Constitution v2.9 (Council Fix Pack Edition)**
+# **ARTICLE XVIII — LIGHTWEIGHT STEWARDSHIP MODE**
+
+> [!NOTE]
+> This article provides a fast-path for routine operations without full gate compliance.
+
+## Section 1. Eligibility Criteria
+
+A mission qualifies for Lightweight Mode if ALL of the following are true:
+
+1. No governance-controlled paths modified (see Article XIII §4)
+2. Total files modified ≤ 5
+3. No new code logic introduced (moves, renames, index updates only)
+4. No council trigger conditions (CT-1 through CT-4) apply
+
+## Section 2. Gate Relaxations
+
+When in Lightweight Mode:
+
+| Standard Gate | Lightweight Behavior |
+|--------------|---------------------|
+| Plan Artefact (Art. XIII) | SKIPPED — proceed directly to execution |
+| Full Flattening (Art. IX) | REPLACED — use Diff-Based Context (see §3) |
+| Review Packet Structure | SIMPLIFIED — Summary + Diff Appendix only |
+| Agent Packet Protocol (Art. XV) | SKIPPED — no YAML packets required |
+
+## Section 3. Diff-Based Context Rules
+
+Instead of verbatim flattening, include:
+
+1. **NEW files (≤100 lines)**: Full content
+2. **NEW files (>100 lines)**: Outline/signatures + first 50 lines
+3. **MODIFIED files**: Unified diff with 10 lines context
+4. **MOVED/RENAMED**: `Before: path → After: path`
+5. **DELETED**: Path only
+
+[Template format included]
+
+## Section 4. Lightweight Review Packet Template
+
+[Simplified markdown template included]
+
+---
+
+# **End of Constitution v3.0 (Lightweight Stewardship Edition)**
```
