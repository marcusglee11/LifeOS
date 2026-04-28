# Agent Control-Plane Pin v1.0

Status: Active dependency contract
Last updated: 2026-04-28

## Purpose

LifeOS treats `marcusglee11/agent-control-plane` as the shared external source for reusable
OpenClaw ↔ Hermes control-plane contracts.

This document defines the LifeOS-side pinning rule. The machine-readable pin is:

```text
config/external_contracts/agent_control_plane_pin.yaml
```

## Boundary

`agent-control-plane` owns reusable protocol/control-plane primitives:

- delegated-authority protocol text
- GitHub bus wire protocol and label/state semantics
- watcher behavior contracts
- shared schemas for authority, evidence, delegation, invocation, and receipts
- protocol probes and reusable operational-discipline standards

LifeOS owns LifeOS-specific surfaces:

- constitutional and governance canon
- roadmap, backlog, and state
- COO runtime and build-loop implementation
- LifeOS-specific architecture decisions

## Pin rule

LifeOS must not depend on a floating branch of `agent-control-plane`.

Every consumed control-plane contract must be represented by:

1. source repo
2. source URL
3. source branch or tag
4. pinned commit SHA
5. consumed source artefact paths
6. LifeOS local target paths, if mirrored
7. compatibility check command
8. PR/issue evidence for each pin bump

## Current pin

The active pin is recorded in `config/external_contracts/agent_control_plane_pin.yaml`.

Current source commit at creation:

```text
df1c4411242c99d65b54775c50aa1fc179f22c0b
```

Source commit URL:

```text
https://github.com/marcusglee11/agent-control-plane/commit/df1c4411242c99d65b54775c50aa1fc179f22c0b
```

## Compatibility check

Default structure-only check:

```bash
python3 scripts/workflow/check_agent_control_plane_pin.py --manifest config/external_contracts/agent_control_plane_pin.yaml
```

Local full check, when the private source repo is available:

```bash
python3 scripts/workflow/check_agent_control_plane_pin.py --manifest config/external_contracts/agent_control_plane_pin.yaml --source-worktree /home/cabra/.openclaw/workspace/agent-control-plane
```

The full check confirms every consumed upstream artefact exists at the pinned source commit.

## Update procedure

1. Inspect upstream diff between the old and candidate `agent-control-plane` commits.
2. Update `config/external_contracts/agent_control_plane_pin.yaml`.
3. Update any mirrored LifeOS artefacts if a consumed path is mirrored locally.
4. Run the compatibility check.
5. Record evidence in the LifeOS PR or issue.

## Extraction procedure

LifeOS-specific decisions land in LifeOS first.

If a decision becomes reusable across Hermes/OpenClaw/other agent surfaces, extract the smallest stable
primitive into `agent-control-plane`. LifeOS then re-consumes it through an explicit pin bump.

Do not smuggle LifeOS governance changes into `agent-control-plane`; do not smuggle reusable protocol
changes into LifeOS without a pin.
