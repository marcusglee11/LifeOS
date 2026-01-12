# Review Packet — Steward OpenCode Config v1.0

**Mission:** Register OpenCode configuration artifacts
**Steward:** Doc Steward (Antigravity)
**Date:** 2026-01-06

## Summary

- Added repository-level OpenCode configuration files.
- Indexed new configuration artifacts in documentation index.
- Regenerated strategic corpus to reflect current repository state.

## Changes

- `AGENTS.md` (new)
- `opencode.json` (new)
- `docs/INDEX.md` (updated)
- `docs/LifeOS_Strategic_Corpus.md` (regenerated)

## Appendix A — Flattened Files

### AGENTS.md

```md
# OpenCode Agent Instructions (Doc Steward Subset)

You are a LifeOS maintenance agent acting as a **Doc Steward**. You MUST adhere to the following LifeOS stewardship protocols.

## Core Directives (Subset of GEMINI.md)

1. **Governance & Authority**: You are subordinate to LifeOS governance. Do not edit `docs/01_governance/` or `docs/00_foundations/` without a Council Ruling.
2. **Review Packet Protocol**: Every mission MUST end with a `Review_Packet_<Mission>_vX.Y.md`.
   - Appendix A MUST contain flattened code for all changed files.
   - Do NOT omit content with ellipses (...).
3. **Doc Stewardship**:
   - If you touch `docs/`, you MUST update `docs/INDEX.md` timestamp.
   - You MUST regenerate `LifeOS_Strategic_Corpus.md`.
4. **Zero-Friction Rule**: Do not ask the user for file lists. Discover them yourself.

## Operational Context

- **State File**: Always check `docs/11_admin/LIFEOS_STATE.md` for current context.
- **Universal Corpus**: Use `docs/LifeOS_Universal_Corpus.md` for deep context if needed.

## Prohibited Patterns

- Never update version numbers in filenames (e.g., `_v2.md`) without creating a NEW file.
- Never write placeholders like `// ... rest of code`.
```

### opencode.json

```json
{
  "instructions": [
    "AGENTS.md",
    "docs/11_admin/LIFEOS_STATE.md"
  ],
  "$schema": "https://opencode.ai/config.json"
}
```

### docs/INDEX.md

```md
# LifeOS# Documentation Index

**Last Updated:** 2026-01-06
**Status:** ACTIVE
**Maintainer:** Antigravity
**Authority**: [LifeOS Constitution v2.0](./00_foundations/LifeOS_Constitution_v2.0.md)

---

## Authority Chain

```
LifeOS Constitution v2.0 (Supreme)
        │
        └── Governance Protocol v1.0
                │
                ├── COO Operating Contract v1.0
                ├── DAP v2.0
                └── COO Runtime Spec v1.0
```

---

## Strategic Context

| Document | Purpose |
|----------|---------|
| [LifeOS_Strategic_Corpus.md](./LifeOS_Strategic_Corpus.md) | **Primary Context for the LifeOS Project** |

---

## Repository Configuration

| File | Purpose |
|------|---------|
| [AGENTS.md](../AGENTS.md) | Agent instructions and stewardship constraints |
| [opencode.json](../opencode.json) | OpenCode agent configuration and instruction roots |

---
```
