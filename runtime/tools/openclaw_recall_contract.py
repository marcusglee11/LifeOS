#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Dict, List

RECALL_INTENT_RE = re.compile(
    r"\b(what\s+did\s+we\s+decide|last\s+week|decision|decide|agreed|recall)\b",
    re.IGNORECASE,
)
HIT_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)?)\s+([^\s:]+:[0-9]+-[0-9]+)\s*$")


def normalize_query(query: str) -> str:
    return " ".join(query.strip().split()).lower()


def query_hash(query: str) -> str:
    return hashlib.sha256(normalize_query(query).encode("utf-8")).hexdigest()


def is_recall_intent(query: str) -> bool:
    return bool(RECALL_INTENT_RE.search(query or ""))


def parse_sources(search_output: str) -> List[str]:
    sources: List[str] = []
    for line in (search_output or "").splitlines():
        m = HIT_RE.match(line)
        if not m:
            continue
        src = m.group(1)
        if src not in sources:
            sources.append(src)
    return sources


def build_contract_response(query: str, search_output: str) -> Dict[str, object]:
    sources = parse_sources(search_output)
    qh = query_hash(query)
    if not is_recall_intent(query):
        return {
            "query_hash": qh,
            "recall_intent": False,
            "hit_count": len(sources),
            "sources": sources,
            "response": "Recall contract not triggered for non-recall intent.",
        }
    if not sources:
        return {
            "query_hash": qh,
            "recall_intent": True,
            "hit_count": 0,
            "sources": [],
            "response": "No grounded memory found. Which timeframe or document should I check?",
        }
    lines = [
        "Grounded recall: available memory evidence indicates this decision was recorded.",
        "",
        "Sources:",
    ]
    lines.extend(f"- {s}" for s in sources)
    return {
        "query_hash": qh,
        "recall_intent": True,
        "hit_count": len(sources),
        "sources": sources,
        "response": "\n".join(lines),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw grounded recall contract helper.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--search-output-file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.search_output_file:
        search_output = open(args.search_output_file, "r", encoding="utf-8", errors="replace").read()
    else:
        search_output = sys.stdin.read()
    result = build_contract_response(args.query, search_output)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(result["response"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
