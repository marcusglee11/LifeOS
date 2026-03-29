# Quality Audit Baseline v1.0

Generated: 2026-03-29T03:40:24.585552Z

## Why This Exists

LifeOS now has a real quality gate, but a gate only proves enforcement exists.
This audit establishes where the repo already conforms, where debt is concentrated,
and what can safely be promoted next without guessing.

## Environment

- Audit environment: Python venv + repo quality toolchain
- Quality doctor passed: `true`
- Tool availability rows: `7`

## Current Standard Conformance

- Repo-scope quality gate passed: `false`
- Summary: command timed out after 60 second(s)
- Advisory tools in current policy: `mypy, yamllint, shellcheck`

## Top Debt Clusters

- `runtime`: 4 failing lane(s) across mypy, pytest, ruff_check, ruff_format
- `doc_steward`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `recursive_kernel`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `project_builder`: 3 failing lane(s) across mypy, ruff_check, ruff_format
- `docs_semantic`: 3 failing lane(s) across doc_steward
- `opencode_governance`: 2 failing lane(s) across ruff_check, ruff_format
- `yaml_shell_json_misc`: 2 failing lane(s) across shellcheck, yamllint
- `scripts_root_config`: 1 failing lane(s) across biome

## Enforcement Chain

- Pre-commit installation status: `not_installed`
- Hook logic evidence: `artifacts/reports/quality_audit_baseline_v1/hook_gate_tests.txt`

## Scope Gaps and Differential Lanes

- Root Markdown outside current quality-gate scope: `955` file(s)
- `opencode_governance` is packaged in `pyproject.toml` but omitted from manifest
  python targets; audited separately as a manifest-scope gap.
- `biome check .` is broader than the day-to-day quality router and is used here
  for baseline signal collection.

## Runtime Baseline Context

- Runtime baseline status: `timed out after 300 second(s) before first failure`
- Runtime failures are contextual baseline evidence only and are not merged into
  the quality findings matrix.

## Promotion Guidance

- Blocking-ready buckets: `docs_semantic, scripts_root_config`
- Keep advisory for now: `doc_steward, docs_markdown_style, docs_semantic,
  project_builder, recursive_kernel, runtime, scripts_root_config,
  yaml_shell_json_misc`
- Exclude or rescope: `opencode_governance`
- Recommended follow-up order: core Python ruff cleanup, biome/docs markdown,
  yamllint/shellcheck promotion decision, mypy by package, manifest decision for
  `opencode_governance`, then any root-Markdown scope expansion.

## Evidence Bundle

- Raw outputs: `artifacts/reports/quality_audit_baseline_v1/`
- Findings matrix: `artifacts/reports/quality_audit_baseline_v1/finding_matrix.json`
- Policy conformance: `artifacts/reports/quality_audit_baseline_v1/quality_gate_repo.json`
