---
title: ""
classification: INTERNAL
retention: 180d
created_utc: 2026-01-01T00:00:00Z
sources:
  - ""
---

# Memory Entry

## Summary

- Briefly describe the fact/decision being stored.

## Evidence

- Provide source pointers that justify this memory (file path, command output, or ticket reference).

## Rules

- Never include secrets, tokens, API keys, passwords, signing secrets, or bearer values.
- Classification must be one of: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`.
- `SECRET` content is disallowed for memory storage.
- Retention must be explicit (`30d`, `180d`, `1y`, or `permanent`).
