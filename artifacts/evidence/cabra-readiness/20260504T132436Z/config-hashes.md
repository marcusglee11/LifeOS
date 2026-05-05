# Config File Hashes (Redacted Evidence)

**Timestamp:** 2026-05-04T13:24:36Z  
**Branch:** fix/codex-only-ea-dispatch  
**HEAD:** 7729cde490307aa8fd72b949e5d96fec199de712

No secret/token content is present in these files. Hashes serve as integrity checksums for the config state at time of inspection.

## SHA-256 Hashes

```
c79c001c068cd9450b95bb9a5e15bd72f04c3c75f7c60b98bdb6a388bfe839ff  config/models.yaml
49773b1faf80fbe02467d9d0b31b6a018a2da6138d6fca278cb8d94bfcf5dd70  config/governance/delegation_envelope.yaml
801a64d4aa2b73c80404416784efb8c359246c0fe548208ad3248676a8e86556  config/governance/active_coo.yaml
6a7aa8b6cb378412873a62f2800575a22ad610efd4077ea4262b34d082634542  config/dispatch.yaml
f86b1ae39e438526f6436ffd7c04b17857bbe8272a9360da87cd2c93680f6732  config/openclaw/instance_profiles/coo.json
1fee2d1f168be11fed8451c35206522b476f88b5ab0a1d51fb33f4fe6a4b79cb  config/coo/telegram_model.json
3899e00e2cb06b764af2729450c1406c618c19168cade4b927142e7f8369e05e  config/policy/posture.yaml
1999237348a0451c341b35b30bd4a0a0bb6af20099cb8f00d163745b755d3ce7  config/tasks/backlog.yaml
```

## API Key Environment Variables

Checked: ZEN_*, ANTHROPIC_*, GITHUB_TOKEN, GH_TOKEN  
Result: **NO matching env vars found in current shell environment.**

This means Zen API gateway calls (claude-sonnet-4-5, glm-5-free, etc.) would fail at runtime in this session. The `gh` CLI token is stored in `/home/cabra/.config/gh/hosts.yml` (managed separately by `gh auth`).

## OpenClaw Binary

```
Path: /home/cabra/bin/openclaw
Size: 62 bytes
Permissions: -rwxr-xr-x
Modified: 2026-04-26 22:49
Version: OpenClaw 2026.4.27 (cbc2ba0)
```

Note: 62 bytes suggests this may be a wrapper script, not the full binary.
