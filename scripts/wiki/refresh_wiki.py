#!/usr/bin/env python3
"""
Wiki refresh script — updates .context/wiki/ pages when source docs change.

Usage:
    python3 scripts/wiki/refresh_wiki.py                        # consume _refresh_needed marker
    python3 scripts/wiki/refresh_wiki.py --changed-files docs/foo.md docs/bar.md
    python3 scripts/wiki/refresh_wiki.py --full

The script identifies which wiki pages are affected (via source_docs frontmatter),
calls Claude via `claude -p` to regenerate those pages, and writes a unified
diff to .context/wiki/_pending_diff.patch for human review.

Wiki pages are NOT auto-committed. Run scripts/wiki/commit_wiki_update.py after review.

Requires: `claude` CLI in PATH (Claude Code session).
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path


WIKI_DIR_REL = ".context/wiki"
SCHEMA_FILE = "SCHEMA.md"
PENDING_DIFF = "_pending_diff.patch"
MARKER_FILE = "_refresh_needed"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True
    )
    return Path(result.stdout.strip())


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


def _read_marker(wiki_dir: Path) -> list[str]:
    """Read and deduplicate changed-file paths from the _refresh_needed marker."""
    marker = wiki_dir / MARKER_FILE
    if not marker.exists() or marker.stat().st_size == 0:
        return []
    lines = marker.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            result.append(line)
    return result


def _clear_marker(wiki_dir: Path) -> None:
    marker = wiki_dir / MARKER_FILE
    if marker.exists():
        marker.unlink()


def _read_source_content(repo_root: Path, source_docs: list[str]) -> str:
    parts: list[str] = []
    for rel in source_docs:
        path = repo_root / rel
        if path.exists():
            parts.append(f"### {rel}\n\n{path.read_text(encoding='utf-8')}")
        else:
            parts.append(f"### {rel}\n\n[FILE NOT FOUND]")
    return "\n\n---\n\n".join(parts)


def _validate_source_docs(page: Path, source_docs: list[str], repo_root: Path) -> list[str]:
    """Return error strings for any invalid source_docs entry. Fail-closed checks."""
    errors = []
    for src in source_docs:
        if not src.startswith("docs/"):
            errors.append(f"{page.name}: source '{src}' is not under docs/ — rejected")
            continue
        abs_path = repo_root / src
        if abs_path.is_dir():
            errors.append(f"{page.name}: source '{src}' is a directory — rejected")
        elif not abs_path.exists():
            errors.append(f"{page.name}: source '{src}' not found — rejected")
    return errors


def _compute_source_commit_max(source_docs: list[str], repo_root: Path) -> str | None:
    """Return the git SHA of the newest commit among source_docs files. Returns None on failure."""
    valid = [s for s in source_docs if s.startswith("docs/") and (repo_root / s).is_file()]
    if not valid:
        return None  # no valid sources — caller must treat this as a rejection
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--"] + valid,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        sha = result.stdout.strip()
        return sha if sha else None
    except (OSError, subprocess.SubprocessError):
        return None


def _call_ea(schema_text: str, page_text: str, sources_text: str) -> str:
    prompt = (
        "You are a wiki maintainer for the LifeOS project. "
        "You update wiki pages in .context/wiki/ when source documentation changes. "
        "Follow the maintenance rules in the SCHEMA.md exactly.\n\n"
        f"## SCHEMA.md\n\n{schema_text}\n\n"
        "The following source documentation has changed. "
        "Update the wiki page to reflect the current state of the sources. "
        "Keep the page compact (200-400 tokens). "
        "Preserve the frontmatter structure. Required frontmatter fields are: "
        "source_docs, source_commit_max, authority, page_class, concepts. "
        "Update source_commit_max to the placeholder string CURRENT_SHA (the caller will "
        "substitute the real SHA). Do NOT emit a last_updated field. "
        "Output ONLY the complete updated wiki page — no explanation, no code fences.\n\n"
        f"## Current wiki page\n\n{page_text}\n\n"
        f"## Changed source docs\n\n{sources_text}"
    )

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"exit {result.returncode}")
    return result.stdout.strip()


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
    parser = argparse.ArgumentParser(description="Refresh LifeOS wiki pages via EA")
    group = parser.add_mutually_exclusive_group(required=False)
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

    # Determine pages to refresh
    from_marker = False
    if args.full:
        pages = _all_pages(wiki_dir)
    elif args.changed_files:
        docs_changed = [f for f in args.changed_files if f.startswith("docs/")]
        if not docs_changed:
            print("No docs/ files changed — wiki refresh skipped.")
            return 0
        pages = _affected_pages(wiki_dir, docs_changed)
        if not pages:
            print("No wiki pages are sourced from the changed files — skipped.")
            return 0
    else:
        # Default: consume _refresh_needed marker
        marker_files = _read_marker(wiki_dir)
        if not marker_files:
            print("No pending wiki refresh (marker empty or absent).")
            return 0
        docs_changed = [f for f in marker_files if f.startswith("docs/")]
        if not docs_changed:
            print("Marker contained no docs/ paths — clearing.")
            _clear_marker(wiki_dir)
            return 0
        pages = _affected_pages(wiki_dir, docs_changed)
        if not pages:
            print("No wiki pages sourced from marker files — clearing.")
            _clear_marker(wiki_dir)
            return 0
        from_marker = True

    print(f"Pages to refresh: {[p.name for p in pages]}")

    # Pre-flight source validation — runs before --dry-run early return
    preflight_errors: list[str] = []
    for page in pages:
        page_sources = _parse_source_docs(page.read_text(encoding="utf-8"))
        preflight_errors.extend(_validate_source_docs(page, page_sources, repo_root))
    if preflight_errors:
        for err in preflight_errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        return 1

    if args.dry_run:
        return 0

    all_diffs: list[str] = []
    errors: list[str] = []

    for page in pages:
        old_text = page.read_text(encoding="utf-8")
        sources = _parse_source_docs(old_text)
        # In-loop guard: validate source_docs before EA call — fail closed
        validation_errors = _validate_source_docs(page, sources, repo_root)
        if validation_errors:
            for err in validation_errors:
                print(f"[ERROR] {err}", file=sys.stderr)
            errors.append(f"{page.name}: skipped — invalid source_docs (see above)")
            continue
        sources_text = _read_source_content(repo_root, sources)

        print(f"  Refreshing {page.name}...", end=" ", flush=True)
        try:
            new_text = _call_ea(schema_text, old_text, sources_text)
            # Compute per-source SHA, fail closed if unavailable
            source_commit_max = _compute_source_commit_max(sources, repo_root)
            if source_commit_max is None:
                errors.append(f"{page.name}: cannot compute source_commit_max — no valid sources resolved")
                continue
            new_text = _substitute_sha(new_text, source_commit_max)
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

    if from_marker and not errors:
        _clear_marker(wiki_dir)

    if errors:
        print(f"\nErrors: {len(errors)}", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
