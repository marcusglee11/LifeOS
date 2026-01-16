"""
Link integrity tests for LifeOS documentation.

Policy: Canonical Surface Only (for now)
- Only validates links within 00_foundations/ and 01_governance/
- See doc_steward/link_checker.py for scope rules
"""
import os
from doc_steward.link_checker import check_links


def test_link_integrity():
    """
    Verify all internal links in canonical docs resolve to existing files.
    
    Scope:
    - docs/00_foundations/
    - docs/01_governance/
    
    Skips:
    - External links (http://, https://, mailto:)
    - Anchor-only links (#...)
    - Template tokens ({...})
    - Files outside canonical roots
    """
    repo_root = os.getcwd()
    docs_root = os.path.join(repo_root, "docs")
    
    # Uses CANONICAL_ROOTS by default (explicit allowlist)
    errors = check_links(docs_root)
    
    assert not errors, f"Broken internal links found:\n" + "\n".join(errors)
