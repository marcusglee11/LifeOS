#!/usr/bin/env python3
"""Fail-closed derived wiki/corpus freshness and provenance merge gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    failures: list[str] = []
    wiki_dir = repo_root / ".context" / "wiki"
    marker = wiki_dir / "_refresh_needed"
    if marker.exists() and marker.read_text(encoding="utf-8").strip():
        failures.append(
            ".context/wiki/_refresh_needed contains pending paths; "
            "run python3 scripts/wiki/refresh_wiki.py and commit reviewed output."
        )

    pending_diff = wiki_dir / "_pending_diff.patch"
    if pending_diff.exists() and pending_diff.read_text(encoding="utf-8").strip():
        failures.append(
            ".context/wiki/_pending_diff.patch contains uncommitted generated diff; "
            "review/apply it with scripts/wiki/commit_wiki_update.py or remove stale diff."
        )

    dry = _run(["python3", "scripts/wiki/refresh_wiki.py", "--dry-run"], repo_root)
    if dry.returncode != 0:
        failures.append((dry.stderr or dry.stdout or "refresh_wiki.py --dry-run failed").strip())
    elif "Pages to refresh:" in dry.stdout:
        failures.append(
            "refresh_wiki.py --dry-run found pages needing refresh; "
            "run python3 scripts/wiki/refresh_wiki.py and commit reviewed output."
        )

    corpus_path = repo_root / "docs" / "LifeOS_Strategic_Corpus.md"
    before_corpus = corpus_path.read_text(encoding="utf-8") if corpus_path.exists() else None
    corpus = _run(["python3", "docs/scripts/generate_strategic_context.py"], repo_root)
    after_corpus = corpus_path.read_text(encoding="utf-8") if corpus_path.exists() else None
    if corpus.returncode != 0:
        failures.append((corpus.stderr or corpus.stdout or "corpus generation failed").strip())
    elif before_corpus != after_corpus:
        failures.append(
            "docs/LifeOS_Strategic_Corpus.md is stale; "
            "run python3 docs/scripts/generate_strategic_context.py and commit output."
        )
        if before_corpus is not None:
            corpus_path.write_text(before_corpus, encoding="utf-8")

    lint = _run(["python3", "-m", "doc_steward.cli", "wiki-lint", "."], repo_root)
    if lint.returncode != 0:
        failures.append((lint.stdout or lint.stderr).strip())

    if failures:
        print("[FAILED] Derived output freshness/provenance gate failed:")
        for failure in failures:
            for line in failure.splitlines():
                print(f"  * {line}")
        return 1

    print("[PASSED] Derived wiki/corpus freshness and provenance gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
