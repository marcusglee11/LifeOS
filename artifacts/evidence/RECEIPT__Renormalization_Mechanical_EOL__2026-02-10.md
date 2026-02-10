# Renormalization Receipt — Mechanical EOL Fix

**Date**: 2026-02-10
**Branch**: `build/eol-clean-invariant`
**Commit**: `e11eae0`
**Type**: Mechanical (zero semantic changes)

---

## Root Cause

| Config Layer | Setting | Effect |
|-------------|---------|--------|
| `.gitattributes` | `* text=auto eol=lf` | Normalize to LF in index |
| System gitconfig | `core.autocrlf=true` | Convert LF→CRLF on checkout |
| Repo-local gitconfig | (was unset) | No override → system wins |

**Result**: 289 files appeared "modified" with zero content changes.

## Fix Applied

```bash
# 1. Override system config at repo level
git config --local core.autocrlf false

# 2. Renormalize index
git add --renormalize .
```

## Semantic-Diff Zero Proof

```
# Command: git diff --cached --ignore-space-at-eol --ignore-cr-at-eol --stat
# Result: (empty — zero semantic diff)
```

All 289 file changes consist exclusively of CRLF→LF line ending normalization.

## Verification Commands

```bash
# Verify zero semantic diff (should output nothing):
git diff --cached --ignore-space-at-eol --ignore-cr-at-eol --stat

# Verify file count matches expected (289):
git diff --cached --name-only | wc -l

# Verify equal insertions/deletions (pure EOL swap):
git diff --cached --stat | tail -1
# Output: 289 files changed, 69026 insertions(+), 69026 deletions(-)
```

## Config Compliance Post-Fix

```
core.autocrlf=false (repo-local override)
Clean-check: CLEAN: working tree clean; core.autocrlf=false (compliant)
```
