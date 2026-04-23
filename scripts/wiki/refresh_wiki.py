#!/usr/bin/env python3
"""
Wiki refresh script — updates .context/wiki/ pages when source docs change.

Usage:
    python3 scripts/wiki/refresh_wiki.py --changed-files docs/foo.md docs/bar.md
    python3 scripts/wiki/refresh_wiki.py --full

The script identifies which wiki pages are affected (via source_docs frontmatter),
calls the Anthropic Messages API to regenerate those pages, and writes a unified
diff to .context/wiki/_pending_diff.patch for human review.

Wiki pages are NOT auto-committed. Run scripts/wiki/commit_wiki_update.py after review.

Requires: ANTHROPIC_API_KEY env var, httpx (pip install httpx)
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import subprocess
import sys
from pathlib import Path


WIKI_DIR_REL = ".context/wiki"
SCHEMA_FILE = "SCHEMA.md"
PENDING_DIFF = "_pending_diff.patch"
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True
    )
    return Path(result.stdout.strip())


def _current_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _parse_source_docs(text: str) -> list[str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return []
    fm = m.group(1)
    in_source = False
    paths: list[str] = []
    for line in fm.splitlines():
        if line.strip().startswith("source_docs:"):
            in_source = True
            continue
        if in_source:
            if line.startswith("  - "):
                paths.append(line.strip().lstrip("- ").strip())
            elif line and not line.startswith(" "):
                break
    return paths


def _affected_pages(wiki_dir: Path, changed_files: list[str]) -> list[Path]:
    """Return wiki pages whose source_docs overlap with changed_files."""
    changed_set = set(changed_files)
    affected: list[Path] = []
    for page in sorted(wiki_dir.glob("*.md")):
        if page.name == SCHEMA_FILE:
            continue
        text = page.read_text(encoding="utf-8")
        sources = _parse_source_docs(text)
        if any(s in changed_set for s in sources):
            affected.append(page)
    return affected


def _all_pages(wiki_dir: Path) -> list[Path]:
    return sorted(p for p in wiki_dir.glob("*.md") if p.name != SCHEMA_FILE)


def _read_source_content(repo_root: Path, source_docs: list[str]) -> str:
    parts: list[str] = []
    for rel in source_docs:
        path = repo_root / rel
        if path.exists():
            parts.append(f"### {rel}\n\n{path.read_text(encoding='utf-8')}")
        else:
            parts.append(f"### {rel}\n\n[FILE NOT FOUND]")
    return "\n\n---\n\n".join(parts)


def _call_api(api_key: str, schema_text: str, page_text: str, sources_text: str) -> str:
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx not installed. Run: pip install httpx", file=sys.stderr)
        sys.exit(1)

    system_prompt = (
        "You are a wiki maintainer for the LifeOS project. "
        "You update wiki pages in .context/wiki/ when source documentation changes. "
        "Follow the maintenance rules in the SCHEMA.md exactly.\n\n"
        f"## SCHEMA.md\n\n{schema_text}"
    )

    user_prompt = (
        "The following source documentation has changed. "
        "Update the wiki page to reflect the current state of the sources. "
        "Keep the page compact (200-400 tokens). "
        "Preserve the frontmatter structure. Update last_updated to the placeholder "
        "string CURRENT_SHA (the caller will substitute the real SHA). "
        "Output ONLY the complete updated wiki page — no explanation, no code fences.\n\n"
        f"## Current wiki page\n\n{page_text}\n\n"
        f"## Changed source docs\n\n{sources_text}"
    )

    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "prompt-caching-2024-07-31",
        "content-type": "application/json",
    }

    response = httpx.post(API_URL, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["content"][0]["text"]


def _substitute_sha(text: str, sha: str) -> str:
    return text.replace("CURRENT_SHA", sha)


def _build_diff(old_text: str, new_text: str, filename: str) -> str:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh LifeOS wiki pages via LLM")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--changed-files", nargs="+", metavar="FILE",
        help="Repo-relative paths of changed source docs"
    )
    group.add_argument(
        "--full", action="store_true",
        help="Regenerate all wiki pages"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print which pages would be updated, then exit"
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        return 1

    repo_root = _repo_root()
    wiki_dir = repo_root / WIKI_DIR_REL

    if not wiki_dir.exists():
        print(f"ERROR: Wiki directory not found: {wiki_dir}", file=sys.stderr)
        return 1

    schema_path = wiki_dir / SCHEMA_FILE
    if not schema_path.exists():
        print(f"ERROR: SCHEMA.md not found: {schema_path}", file=sys.stderr)
        return 1

    schema_text = schema_path.read_text(encoding="utf-8")

    if args.full:
        pages = _all_pages(wiki_dir)
    else:
        # Filter changed files to only those under docs/
        docs_changed = [f for f in args.changed_files if f.startswith("docs/")]
        if not docs_changed:
            print("No docs/ files changed — wiki refresh skipped.")
            return 0
        pages = _affected_pages(wiki_dir, docs_changed)
        if not pages:
            print("No wiki pages are sourced from the changed files — skipped.")
            return 0

    print(f"Pages to refresh: {[p.name for p in pages]}")

    if args.dry_run:
        return 0

    sha = _current_sha()
    all_diffs: list[str] = []
    errors: list[str] = []

    for page in pages:
        old_text = page.read_text(encoding="utf-8")
        sources = _parse_source_docs(old_text)
        sources_text = _read_source_content(repo_root, sources)

        print(f"  Refreshing {page.name}...", end=" ", flush=True)
        try:
            new_text = _call_api(api_key, schema_text, old_text, sources_text)
            new_text = _substitute_sha(new_text, sha)
            if not new_text.endswith("\n"):
                new_text += "\n"

            diff = _build_diff(old_text, new_text, str(page.relative_to(repo_root)))
            if diff:
                all_diffs.append(diff)
                page.write_text(new_text, encoding="utf-8")
                print("updated")
            else:
                print("no changes")
        except Exception as exc:
            print(f"ERROR: {exc}")
            errors.append(f"{page.name}: {exc}")

    # Write pending diff
    pending_path = wiki_dir / PENDING_DIFF
    if all_diffs:
        combined = "".join(all_diffs)
        pending_path.write_text(combined, encoding="utf-8")
        print(f"\nDiff written to: {pending_path}")
        print("Review it, then run: python3 scripts/wiki/commit_wiki_update.py")
    else:
        if pending_path.exists():
            pending_path.unlink()
        print("\nNo changes to wiki pages.")

    if errors:
        print(f"\nErrors: {len(errors)}", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
