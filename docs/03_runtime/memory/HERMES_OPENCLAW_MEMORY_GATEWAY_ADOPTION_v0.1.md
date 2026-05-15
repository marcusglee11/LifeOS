# Hermes/OpenClaw Memory Gateway Adoption v0.1

Authority: `docs/03_runtime/memory/LIFEOS_MEMORY_KNOWLEDGE_ARCHITECTURE_v0.5.md` and `docs/03_runtime/memory/LIFEOS_MEMORY_PHASE1_OPERATING_CONTRACT.md`.

Tracker: [LifeOS #129](https://github.com/marcusglee11/LifeOS/issues/129).

## Purpose

Prove the operational adoption path for Hermes and OpenClaw using LifeOS Memory Gateway v0.1
without changing the architecture or granting either agent durable-memory write authority.

## Non-negotiable boundary

```text
native agent memory = observations/preferences/local behavior hints
knowledge-staging = candidate packets
LifeOS memory/ = reviewed durable records
gateway = governed interface, not authority
```

The gateway exposes only:

- `memory.retrieve` — read governed LifeOS memory under retrieval rules.
- `memory.capture_candidate` — write candidate packets and session logs under `knowledge-staging/` only.

It must not expose promotion, receipt, durable-write, git, GitHub, subprocess, native-memory mutation, or automation tools.

## Agent adoption flow

### 1. Retrieve governed context

Hermes or OpenClaw may call `memory.retrieve` when an operator-approved workflow needs existing LifeOS memory context.

Minimum call shape:

```json
{
  "session_id": "<agent-session-id>",
  "query": "<operator objective or memory question>",
  "scope": "workflow",
  "authority_floor": "observation",
  "include_sensitive": false,
  "limit": 10
}
```

Rules:

- Treat retrieval output as context, not permission to mutate canon.
- Keep `include_sensitive` false unless a separate explicit workflow authorizes sensitive readback.
- Record the session log under `knowledge-staging/_sessions/` as evidence of the gateway call.

### 2. Emit candidate packets, not durable records

If Hermes or OpenClaw observes something that may deserve durable LifeOS memory, it may call
`memory.capture_candidate` through the gateway.

Minimum call shape:

```json
{
  "session_id": "<agent-session-id>",
  "agent": "Hermes|OpenClaw",
  "iso_timestamp": "<UTC timestamp>",
  "summary": "<one-sentence candidate summary>",
  "proposed_action": "create",
  "proposed_record_kind": "lesson",
  "proposed_authority_class": "agent_memory",
  "scope": "workflow",
  "sensitivity": "internal",
  "personal_inference": false,
  "promotion_basis": "Why this should be reviewed by COO before any durable write.",
  "sources": [
    {
      "source_type": "issue",
      "locator": "https://github.com/marcusglee11/LifeOS/issues/129",
      "quoted_evidence": "Non-sensitive evidence excerpt.",
      "captured_utc": "<UTC timestamp>"
    }
  ],
  "payload": {
    "title": "<candidate title>",
    "expected_future_effect": "<what behavior improves if reviewed and accepted>"
  }
}
```

Rules:

- Candidate output belongs in `knowledge-staging/cand-*.md`.
- Session evidence belongs in `knowledge-staging/_sessions/*.jsonl`.
- Failed/invalid candidate attempts belong in `knowledge-staging/_failed/` when the existing gateway logic persists them.
- Durable records under `memory/` remain COO-reviewed repo artifacts only.

### 3. Review boundary

A candidate packet is not accepted memory. Promotion requires the existing review path:

1. Candidate packet is committed to a branch or presented in a PR.
2. COO review accepts, rejects, stages, or merges it.
3. Accepted durable records move to `memory/` with `writer: COO` and receipts.
4. Rejected/staged/merged dispositions are recorded through durable receipt semantics.

## Smoke checklist

Use this checklist for Hermes/OpenClaw adoption proof runs:

- [ ] `tools/memory/mcp_server.py` lists exactly `memory.retrieve` and `memory.capture_candidate`.
- [ ] `memory.retrieve` returns governed context and appends a session JSONL line.
- [ ] `memory.capture_candidate` creates only `knowledge-staging/cand-*.md` plus session/failed
  evidence under `knowledge-staging/`.
- [ ] A direct or implied `memory.promote`, `memory.write`, `memory.receipt`, `git`, `gh`, or
  subprocess path fails closed or is absent.
- [ ] `python3 tools/memory/validate.py knowledge-staging` passes.
- [ ] `python3 tools/memory/validate.py memory` passes.
- [ ] `git diff --name-status -- memory` is empty for the adoption proof.
- [ ] OpenClaw review confirms both agents can use the flow and no direct durable-memory authority was introduced.

## Dogfood evidence from #129

This slice dogfoods the gateway by creating a non-sensitive candidate packet about the adoption proof
itself. The candidate is intentionally staged only; it must not be promoted to `memory/` by this PR.

Expected evidence shape:

- candidate file: `knowledge-staging/cand-*.md`
- session file: `knowledge-staging/_sessions/issue-129-hermes-adoption.jsonl`
- durable-memory diff: none
- validation commands: `python3 tools/memory/validate.py knowledge-staging` and `python3 tools/memory/validate.py memory`

## Phase 2/3 deferrals

This v0.1 adoption proof does not implement:

- continuous sync from native agent memories;
- unattended promotion or review;
- vector indexes, embeddings, ranking, or reranking;
- credential changes or gateway service restarts;
- public/external repo writes;
- native Hermes or OpenClaw memory mutation;
- OpenClaw readiness closure beyond recording current review evidence.
