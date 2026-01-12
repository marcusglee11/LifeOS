# Platform Policy

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux | ✅ Primary | CI target, production |
| macOS | ✅ Supported | Development |
| Windows (native) | ❌ Unsupported | Use WSL2 |

## Path Handling

The Stewardship Runner rejects Windows-style paths at config validation:
- `C:\path` → rejected (`absolute_path_windows`)
- `\\server\share` → rejected (`absolute_path_unc`)

This is a **safety net**, not runtime support. The runner is not tested on Windows.

## Contributors on Windows

Use WSL2 with Ubuntu. The LifeOS toolchain assumes POSIX semantics.

## Rationale

Maintaining cross-platform compatibility adds complexity without benefit.
LifeOS targets server/CI environments (Linux) and developer machines (Linux/macOS).
