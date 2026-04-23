# Plan: Cut close-build friction for small changes

## 1. Context

User: “LifeOS starting to be a red-tape machine.” Small doc/config edits are paying disproportionate close-time cost. Goal: proportional work for proportional change.

Scope is scripts-only. No governance/protocol text edits are in scope.

The existing 5-tier closure system remains the base. This change set addresses four concrete bottlenecks while preserving safety:

1. Doc stewardship currently walks whole trees for narrow doc edits.
2. Quality-gate routing fans one changed `.md` or `.yml` into all tracked files of that type.
3. There is no safe config-only light tier for clearly non-operational config.
4. Branch kind is parsed but not used to relax only the genuinely safe subset of closure work.

## 2. Invariants

1. Targeted pytest stays on for non-doc changes. No `--fast` escape hatch.
2. Structural doc invariants remain full-tree checks even when content/path checks are narrowed.
3. `config/tasks/` is operational config and must **not** be treated as light-tier config.
4. Branch naming must **not** suppress ceremony for generic `full` changes.
5. Mixed change sets still escalate to the highest-risk tier.

## 3. Approach

### 3.1 Fix 1 — Scope doc stewardship to changed docs

**Files**
- `doc_steward/cli.py`
- `doc_steward/dap_validator.py`
- `doc_steward/link_checker.py`
- `doc_steward/admin_structure_validator.py`
- `doc_steward/admin_archive_link_ban_validator.py`
- `doc_steward/protocols_structure_validator.py`
- `doc_steward/runtime_structure_validator.py`
- `doc_steward/archive_structure_validator.py`
- `doc_steward/global_archive_link_ban_validator.py`
- `runtime/tools/workflow_pack.py`

**CLI changes**
Add optional `--paths` to these subcommands in `doc_steward/cli.py`:
- `dap-validate`
- `link-check`
- `admin-structure-check`
- `admin-archive-link-ban-check`
- `protocols-structure-check`
- `runtime-structure-check`
- `archive-structure-check`
- `docs-archive-link-ban-check`

Use:
- `nargs='+'`
- `default=None`

Do not allow `--paths` with zero values.

Thread `args.paths` through to each corresponding `check_*` function.

**Validator changes**
Extend each `check_*` signature to accept:

```python
paths: Sequence[str] | None = None
```

Behavior:
1. Normalize all provided paths to repo-relative POSIX form before use.
2. When `paths is None`, preserve current behavior.
3. When `paths` is provided:
   - compute the validator’s canonical candidate `.md` set as today
   - intersect that set with the normalized provided paths
   - run content/path-level validation only on the intersected set
4. Structural invariants must still run unconditionally across the full canonical tree:
   - required files
   - required directories
   - required structure rules

This narrowing is for file-level scanning only, not for structural integrity checks.

**Workflow wiring**
In `runtime/tools/workflow_pack.py`, inside `check_doc_stewardship`:
1. Keep the existing prefix guards that determine whether each validator should run.
2. For each `doc_steward.cli` invocation, filter `changed_files` to the matching subtree.
3. Pass `--paths <filtered paths...>` only when the filtered list is non-empty.
4. Do not pass `--paths` to `artefact-index-check`; keep that whole-directory.

Deleted or renamed files must not cause path-passing crashes:
- ignore deleted paths when constructing `--paths`
- only pass paths that still exist in the working tree for validators that read file contents

### 3.2 Fix 2 — Kill quality-gate category fan-out

**File**
- `runtime/tools/workflow_pack.py`

In the quality-tool routing logic, remove the fallback blocks that expand:
- one changed `.md` into all tracked markdown files
- one changed `.yml`/`.yaml` into all tracked yaml files

Keep only direct changed-file routing:

```python
if markdown_trigger and markdown_files:
    routed["markdownlint"] = _unique_ordered(markdown_files)

if yaml_trigger and yaml_files:
    routed["yamllint"] = _unique_ordered(yaml_files)
```

Per-file command building already handles empty lists. Repo-wide quality checks remain available through the explicit repo-scope path and must not be auto-forced during narrow close flows.

### 3.3 Fix 3 — Add `config_light` closure tier

**File**
- `runtime/tools/closure_policy.py`

Add:

```python
_CONFIG_LIGHT_PREFIXES = (
    "config/governance/",
    "config/quality/",
)
```

Do **not** include `config/tasks/`.

**Path classification**
In `_classify_path`:
1. Before `_FULL_PREFIXES` handling, check `_CONFIG_LIGHT_PREFIXES`.
2. If the path is under one of those prefixes and suffix is one of:
   - `.yml`
   - `.yaml`
   - `.toml`
   return `"config_light"`.
3. Any other suffix under `config/` falls through to `"full"`.

**Path-set classification**
In `classify_paths`:
1. If categories are exactly `{"config_light"}`, return the `config_light` tier result.
2. Any mixed set involving `config_light` and anything else falls through to the highest-risk tier, which remains `full`.

**Execution policy**
In `get_tier_execution_policy`, add a `config_light` policy entry with:

- `selected_checks = ["yamllint", "targeted_pytest"]`
- `skipped_checks = ["quality_gate", "doc_stewardship", "markdownlint", "review_checkpoint", "runtime_status_regeneration", "state_backlog_updates", "structured_backlog_updates"]`
- `run_targeted_pytest = True`
- `targeted_pytest_commands = []`
- `quality_tools = ["yamllint"]`
- `post_merge_updates_suppressed = True`

This relies on existing targeted-test routing to select the relevant config-scoped tests.

`config/tasks/` remains `full` and therefore keeps full ceremony.

### 3.4 Fix 4 — Kind-aware closure policy, but only for safe light-tier config

**Files**
- `runtime/tools/closure_policy.py`
- `scripts/workflow/closure_pack.py`
- `scripts/workflow/closure_gate.py`

Extend the signature of `get_tier_execution_policy` to:

```python
def get_tier_execution_policy(
    closure_tier: str,
    branch_kind: str | None = None,
    changed_paths: Sequence[str] | None = None,
) -> dict:
```

**Policy rule**
When:
- `branch_kind in {"fix", "hotfix"}`
- and `closure_tier == "config_light"`

override the returned policy to suppress:
- `run_state_backlog_updates = False`
- `run_structured_backlog_updates = False`
- `run_runtime_status_regeneration = False`
- `run_review_checkpoint = False`

Do **not** apply any branch-kind suppression to generic `full`.

That means:
- `fix/` and `hotfix/` branches get lighter closure only for safe `config_light` edits
- `fix/` and `hotfix/` branches with runtime/code/operational-task changes still run full ceremony

**Caller plumbing**
- In `scripts/workflow/closure_pack.py`, reuse existing branch-kind parsing and pass:
  - `branch_kind=kind`
  - `changed_paths=tier_info["changed_paths"]`
- In `scripts/workflow/closure_gate.py`, parse branch kind from the branch arg and pass it through the same way

Default `branch_kind=None` must preserve current behavior for callers that do not supply it.

## 4. Critical files

- `runtime/tools/closure_policy.py`
- `runtime/tools/workflow_pack.py`
- `doc_steward/cli.py`
- `doc_steward/dap_validator.py`
- `doc_steward/link_checker.py`
- `doc_steward/admin_structure_validator.py`
- `doc_steward/admin_archive_link_ban_validator.py`
- `doc_steward/protocols_structure_validator.py`
- `doc_steward/runtime_structure_validator.py`
- `doc_steward/archive_structure_validator.py`
- `doc_steward/global_archive_link_ban_validator.py`
- `scripts/workflow/closure_pack.py`
- `scripts/workflow/closure_gate.py`

## 5. Tests

### 5.1 `runtime/tests/test_closure_policy.py`

Add:
- `test_classify_paths_config_light_yaml_only`
- `test_classify_paths_config_tasks_yaml_is_full`
- `test_classify_paths_config_light_python_falls_to_full`
- `test_classify_paths_config_light_mixed_with_runtime_falls_to_full`
- `test_get_tier_execution_policy_config_light`
- `test_get_tier_execution_policy_fix_branch_skips_backlog_updates_for_config_light`
- `test_get_tier_execution_policy_fix_branch_does_not_relax_generic_full`
- `test_get_tier_execution_policy_hotfix_branch_behaves_like_fix`

### 5.2 `runtime/tests/test_workflow_pack.py`

Add:
- `test_route_quality_tools_no_markdown_fan_out`
- `test_route_quality_tools_no_yaml_fan_out`
- `test_check_doc_stewardship_passes_paths_arg`
- `test_check_doc_stewardship_skips_subtree_validators_when_no_matching_changes`
- `test_check_doc_stewardship_ignores_deleted_paths_when_building_paths_args`

### 5.3 Doc-steward validator tests

Add tests covering:
- `paths` narrows scanned files
- path normalization to repo-relative POSIX form
- structural invariants still run full-tree even when `paths` is supplied
- deleted/nonexistent paths are ignored safely

### 5.4 `runtime/tests/test_closure_gate.py`

Add:
- test that branch kind is plumbed through
- test that `fix/` + `config_light` suppresses backlog/review/runtime-status work
- test that `fix/` + `full` does **not** suppress full ceremony

## 6. Risk and rollback

### 6.1 Narrow doc validators
Risk: a content-level issue in an untouched file is not caught during a narrow close.

Mitigation:
- full structural invariants still run
- repo-wide quality and full doc validation paths remain available explicitly

Rollback:
- remove `--paths` from callers and validators revert to full scan behavior

### 6.2 `config_light` misses a config regression
Risk: a non-operational config edit still affects runtime unexpectedly.

Mitigation:
- `config_light` is restricted to `config/governance/` and `config/quality/`
- targeted pytest remains on
- `config/tasks/` stays `full`

Rollback:
- remove `_CONFIG_LIGHT_PREFIXES` and all such changes fall back to `full`

### 6.3 Branch-kind suppression becomes a bypass
Risk: `fix/` naming suppresses needed ceremony.

Mitigation:
- suppression is allowed only for `config_light`
- no suppression for generic `full`

Rollback:
- remove branch-kind override logic entirely

## 7. Verification

1. Run `pytest runtime/tests -q` and confirm green.
2. Create a scratch docs-only branch touching one `.md`; run:
   - `python3 scripts/workflow/close_build.py --dry-run`
   Assert:
   - `dap-validate` receives `--paths <that file>`
   - `markdownlint` receives exactly that one changed file
   - no full pytest is triggered
3. Create a scratch `build/` branch changing one `config/governance/*.yml`; dry-run close and assert:
   - tier resolves `config_light`
   - `yamllint` runs on exactly that file
   - targeted pytest runs only the relevant routed tests
   - no review checkpoint, runtime status regeneration, or backlog updates run
4. Create a scratch `build/` branch changing one `config/tasks/*.yml`; dry-run close and assert:
   - tier resolves `full`
   - full ceremony remains on
5. Create a scratch `fix/` branch changing one `config/governance/*.yml`; dry-run close and assert:
   - tier resolves `config_light`
   - review checkpoint, runtime status regeneration, and backlog updates are suppressed
   - targeted pytest still runs
6. Create a scratch `fix/` branch with a runtime edit; dry-run close and assert:
   - tier resolves `full`
   - full ceremony still runs
   - no branch-name bypass occurs
7. Run a normal `build/` branch full close and confirm existing full-tier behavior is unchanged.

## 8. Execution note

Implement exactly the above. Do not widen scope. Do not add new tiers beyond `config_light`. Do not change governance/protocol documents. Do not introduce a fast-path that disables targeted pytest.
