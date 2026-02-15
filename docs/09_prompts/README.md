# Agent Prompt Templates

Agent role prompts, system messages, and reviewer templates.

## Versioning Strategy

Prompts are organized by version, with each version directory containing a complete set of prompts for that release.

### Active Versions

- **v1.2/** - Current active prompt set (12 reviewer prompts + chair/cochair)
  - Council chair and co-chair prompts
  - 10 specialized reviewer prompts (alignment, architect, determinism, governance, etc.)

- **v1.0/** - Legacy prompt structure (deprecated but preserved)
  - Contains older organizational structure (initialisers/, protocols/, roles/, system/)
  - Superseded by v1.2 flat structure

### Version Selection

**Default:** Use v1.2/ prompts for all current operations.

**Legacy compatibility:** v1.0/ structure preserved for reference but should not be actively used.

## Directory Structure

```
docs/09_prompts/
├── v1.0/           # Legacy (deprecated)
│   ├── initialisers/
│   ├── protocols/
│   ├── roles/
│   └── system/
└── v1.2/           # Current (active)
    ├── chair_prompt_v1.2.md
    ├── cochair_prompt_v1.2.md
    └── reviewer_*.md (10 specialized reviewers)
```

## Related Directories

- **docs/05_agents/**: Agent specifications
- **docs/01_governance/**: Agent constitutions
- **docs/02_protocols/**: Agent interaction protocols

## Future Versioning

When creating v1.3 or later versions:
1. Create new version directory (e.g., `v1.3/`)
2. Copy relevant prompts from previous version
3. Update this README to mark previous version as legacy
4. Update default version reference

**Archiving rule:** Do not delete old version directories. They serve as historical reference for prompt evolution.

## Status

Active - v1.2 is canonical prompt set.
