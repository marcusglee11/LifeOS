# Plan: Tier-3 Infrastructure — CLI & Config Kickoff

Bootstrap the Tier-3 execution layer.

## User Review Required
> [!NOTE]
> This is a structural kickoff; no production logic implemented in this increment.

## Proposed Changes

### [Component] Tier-3 CLI
Establish the package structure and entry point.

#### [NEW] [coo/cli/__init__.py](coo/cli/__init__.py)
Package marker.

#### [NEW] [coo/cli/main.py](coo/cli/main.py)
Initial CLI entrypoint with `--version` and `--help`.

### [Component] Tier-3 Config
Establish the configuration loading layer.

#### [NEW] [coo/config/loader.py](coo/config/loader.py)
Skeleton for deterministic config loading.

## Verification Plan
- `python -m coo.cli.main --help`
- `pytest coo/tests/test_cli_smoke.py`
