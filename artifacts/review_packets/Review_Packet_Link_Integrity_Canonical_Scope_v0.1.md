# Review_Packet_Link_Integrity_Canonical_Scope_v0.1

**Mission**: Fix test_link_integrity via Canonical Surface Scope  
**Date**: 2026-01-02  
**Author**: Antigravity Agent  
**Status**: COMPLETE

---

## 1. Summary

Scoped link checker to canonical docs only. **Policy: canonical surface (for now)**.

---

## 2. Verification

```bash
python -m pytest -q -c pytest.ini runtime/tests tests_doc tests_recursive
# Result: 347 passed, 1 skipped
```

---

## 3. Changes

### link_checker.py

- Added `CANONICAL_ROOTS = ["00_foundations", "01_governance"]` explicit allowlist
- `check_links(doc_root, canonical_roots=None)` accepts override list (defaulted)
- Only walks directories in allowlist (no heuristics)
- Template token skip uses regex: `re.search(r"\{[^}]+\}", link)` (tighter than broad `{` check)

### test_links.py

- Simplified to use scoped `check_links()` with default canonical roots

---

## 4. Policy

**Canonical surface only (for now)**:
- `docs/00_foundations/`
- `docs/01_governance/`

---

## Appendix — Key Code

### Template Token Skip (regex)

```python
# Must match {token} pattern, not just any brace character
if re.search(r"\{[^}]+\}", link):
    return None
```

---

## End of Review Packet
