# BLOCKED: P0.1 - pyproject.toml Packaging Metadata Authorization Required

**Date:** 2026-01-13
**Blocker:** E.P0.1 from Post-Review Instruction Block
**Status:** BLOCKED - Awaiting CEO Authorization

## Issue

The Tier-3 Mission Dispatch Wiring v1.0 implementation added complete Python packaging metadata to `pyproject.toml`, expanding it from a placeholder comment to a full PEP 621 project definition with:
- [project] metadata (name, version, description, dependencies)
- [project.optional-dependencies] for dev tools
- [project.scripts] for console script entry point
- [build-system] configuration

## Evidence

**Original content** (git commit 24fd9a9):
```toml
# Project Metadata
```

**Added content** (Tier-3 Mission Dispatch v1.0):
```toml
# Project Metadata

[project]
name = "lifeos"
version = "0.1.0"
description = "A personal operating system that makes you the CEO of your life"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "httpx>=0.27.0",
    "requests>=2.31.0",
    "jsonschema>=4.21.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "types-PyYAML>=6.0",
]

[project.scripts]
lifeos = "runtime.cli:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

## Repository Context

The repository's current usage model (per CLAUDE.md):
- **Installation:** `pip install -r requirements.txt` (not `pip install -e .`)
- **Module execution:** `python -m runtime.cli` (not `lifeos` console script)
- **No setup.py or setup.cfg** in git history
- **No packaging metadata** existed before this mission

## Post-Review Instruction (E.P0.1)

> "If the repo truly had only a placeholder comment and no packaging metadata: STOP and emit BLOCKED report asking for explicit authorization to establish packaging metadata (do not invent dependencies/build backend unilaterally)."

## Action Taken

1. **Reverted** `pyproject.toml` to original placeholder content
2. **Created** this BLOCKED report
3. **Proceeding** with other post-review fixes (P0.2, P1.x) which are independent

## Authorization Request

**Question for CEO:** Should LifeOS establish Python packaging metadata to support:
1. Console script installation (`lifeos` command)
2. Pip-installable package distribution
3. PEP 621-compliant project metadata

**If YES:**
- Approve the packaging metadata structure shown above, OR
- Provide alternative packaging configuration

**If NO:**
- Keep `pyproject.toml` as placeholder
- Remove console script functionality from scope
- Continue using `python -m runtime.cli` invocation pattern

## Impact Assessment

**If packaging metadata NOT authorized:**
- P1.2 console script entry point becomes N/A
- CLI remains usable via `python -m runtime.cli mission list/run`
- No functional regression (all tests still pass)
- Review packet accuracy: P0/P1 distinction remains valid

**If packaging metadata authorized:**
- Users can install with `pip install -e .`
- Console script `lifeos` becomes available
- Aligns with standard Python package distribution practices
- Requires explicit dependency list maintenance

## Recommendation

Given the repo's current "development workspace" model (not distributed package), **recommend NO packaging metadata** unless there's a specific goal to distribute LifeOS as an installable package.

Alternative: If only console script is desired, use minimal addition:
```toml
[project]
name = "lifeos"
version = "0.1.0"

[project.scripts]
lifeos = "runtime.cli:main"
```

But this still requires authorization per instruction block.
