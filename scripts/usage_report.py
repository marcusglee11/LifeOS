#!/usr/bin/env python
"""
Usage Report Generator for LifeOS Agent Calls.

Reads logs from logs/agent_calls/ and generates a summary by role and model.

Usage:
    python scripts/usage_report.py
"""
import json
import os
from collections import defaultdict
from pathlib import Path


def generate_report(logs_dir: str = "logs/agent_calls") -> None:
    """Generate and print usage report from agent call logs."""
    logs_path = Path(logs_dir)
    if not logs_path.exists():
        print(f"Logs directory not found: {logs_dir}")
        return

    # Aggregate data
    by_role = defaultdict(lambda: {"calls": 0, "total_latency_ms": 0})
    by_model = defaultdict(lambda: {"calls": 0, "total_latency_ms": 0})
    by_role_model = defaultdict(lambda: {"calls": 0, "total_latency_ms": 0})

    for f in logs_path.glob("*.json"):
        try:
            with open(f) as fp:
                entry = json.load(fp)
            role = entry.get("role", "unknown")
            model = entry.get("response", {}).get("model_used", "unknown")
            latency = entry.get("response", {}).get("latency_ms", 0)

            by_role[role]["calls"] += 1
            by_role[role]["total_latency_ms"] += latency

            by_model[model]["calls"] += 1
            by_model[model]["total_latency_ms"] += latency

            key = f"{role} -> {model}"
            by_role_model[key]["calls"] += 1
            by_role_model[key]["total_latency_ms"] += latency
        except Exception:
            pass

    # Print report
    print()
    print("=" * 70)
    print("LIFEOS USAGE REPORT")
    print("=" * 70)

    print("\n--- BY ROLE ---")
    print(f"{'Role':<30} {'Calls':>8} {'Avg Latency':>12}")
    print("-" * 52)
    for role, stats in sorted(by_role.items()):
        avg = stats["total_latency_ms"] / stats["calls"] if stats["calls"] else 0
        print(f"{role:<30} {stats['calls']:>8} {avg:>10.0f}ms")

    print("\n--- BY MODEL ---")
    print(f"{'Model':<40} {'Calls':>8} {'Avg Latency':>12}")
    print("-" * 62)
    for model, stats in sorted(by_model.items()):
        avg = stats["total_latency_ms"] / stats["calls"] if stats["calls"] else 0
        print(f"{model:<40} {stats['calls']:>8} {avg:>10.0f}ms")

    print("\n--- BY ROLE + MODEL ---")
    print(f"{'Role -> Model':<50} {'Calls':>8} {'Avg Latency':>12}")
    print("-" * 72)
    for combo, stats in sorted(by_role_model.items()):
        avg = stats["total_latency_ms"] / stats["calls"] if stats["calls"] else 0
        print(f"{combo:<50} {stats['calls']:>8} {avg:>10.0f}ms")

    total = sum(s["calls"] for s in by_model.values())
    print("-" * 72)
    print(f"Total calls: {total}")
    print()


if __name__ == "__main__":
    generate_report()
