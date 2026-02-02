# Autonomy Project Baseline (to avoid future “audit weeks”)
## v1.0 — Minimal Canonical Docs + Maintenance Protocol

This is a “small-but-sufficient” project management layer specifically for autonomous build loops.

---

## A. Canonical Doc Set (keep it tiny)

1) **AUTONOMY_STATUS.md**
- Single page: capability matrix (exists/partial/missing), current blockers, “next build” recommendation.
- Updated only when a phase closes or a blocker changes state.

2) **AUTONOMY_ROADMAP.md**
- The phase order, acceptance criteria, and dependencies (this revised Roadmap v1.1 content).

3) **AUTONOMY_INTERFACE_CONTRACT.md**
- The stable handoff schema between:
  - Orchestrator (Antigravity now)
  - Agents (OpenCode designer/reviewer/builder/steward)
- If this contract stays stable, you can swap agents without re-auditing everything.

4) **AUTONOMY_RUNBOOK.md**
- “How to run one loop” (commands)
- “How to resume after checkpoint”
- “How to interpret a failed run / where evidence lives”

5) **AUTONOMY_CHANGELOG.md**
- One-line entries only:
  - date, commit, what capability changed, which acceptance criterion is now satisfied

6) **AUTONOMY_PACK_CONTRACT.md**
- Defines the “Status Pack” format (≤10 files zip) so any agent can generate it, and you can re-baseline in minutes.

That’s it. If you keep these 6 current, you don’t need big audits.

---

## B. The Status Pack Protocol (so updates are low-friction)

Create (or standardize) a single command/script that generates a zip with <=10 flat files:

**Zip name:** `Repo_Autonomy_Status_Pack__YYYYMMDD.zip`  
**Files (suggested 8–10):**
1) `RepoSnapshot.txt` (branch, HEAD, status porcelain, last 10 commits)
2) `AutonomyCapabilityMatrix.md` (auto-generated from greps + known file presence)
3) `KeyFilesPresence.txt` (exists/missing list for loop spine, queue, backlog parser, envelope)
4) `TestSummary.txt` (commands + pass/fail counts)
5) `RunbookExtract.md` (current recommended run command(s))
6) `OpenIssues.txt` (top blockers from BACKLOG/LIFEOS_STATE)
7) `MANIFEST.txt` (file list + sha256 of each file)

**Rule:** Every time you ask “where are we now?”, you attach the latest pack, and the assistant updates AUTONOMY_STATUS.md in one pass.

---

## C. Governance / Review Tiering (keep aligned with Council Protocol)

Use Council Protocol v1.3 modes:
- **M0_FAST**: design iterations / low-risk refactors
- **M1_STANDARD**: implementation plans + review packets
- Escalate to independence only when the protocol says governance/runtime-core touch requires it. :contentReference[oaicite:26]{index=26}

This avoids “hash nitpicks” becoming a permanent tax while preserving real safety gates.

---

## D. Operational Cadence (minimal overhead)
- When a Phase closes: update AUTONOMY_STATUS.md + AUTONOMY_CHANGELOG.md (2 minutes)
- Weekly (or per meaningful change): regenerate Status Pack and keep the latest one attached to your running thread

---
