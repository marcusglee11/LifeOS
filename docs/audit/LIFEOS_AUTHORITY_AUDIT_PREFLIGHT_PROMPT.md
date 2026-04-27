# LifeOS Authority Audit — Preflight Prompt

Use this prompt with a normal agent/model before spending a Pro-level Thinking query.

```text
You are preparing context for a later Pro-level Thinking audit.

Repository context:
- Repo: marcusglee11/LifeOS
- Branch: main
- Pinned audit commit: d94e51afd1c076393a32d7d7e94e893a33e82185
- Manifest: docs/audit/LIFEOS_AUTHORITY_AUDIT_MANIFEST.md

Task:
Inspect the manifest and the connected GitHub repo at the pinned commit.

Do not perform the architecture audit.
Do not propose architecture fixes.
Do not broaden into web research.
Do not use memory from other chats.

Verify:
1. Whether categories A–F are sufficiently populated.
2. Whether every listed path exists at the pinned commit.
3. Whether proposal-only, stale, superseded, or archive docs are clearly marked.
4. Whether representative examples in category G are adequate.
5. Whether any missing artefacts would invalidate the later Pro audit.

Output only:

A. CONTEXT SUFFICIENCY VERDICT
- SUFFICIENT / PARTIAL / INSUFFICIENT

B. MISSING OR WEAK CONTEXT
- category
- missing/weak artefact
- why required

C. PATH VALIDATION
- found
- missing
- ambiguous

D. CANONICALITY VALIDATION
- canonical surfaces confirmed
- proposal/stale/archive surfaces confirmed
- unresolved canonicality risks

E. DO NOT SPEND PRO QUERY YET?
- yes/no
- reason

Acceptance rule:
Only answer NO under section E if categories A–F are populated, paths resolve, and canonicality/draft distinctions are clear enough for the later audit.
```
