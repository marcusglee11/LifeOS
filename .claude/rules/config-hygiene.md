---
paths: [".claude/**"]
---
# Config Hygiene

- `.claude/settings.local.json` should be empty (`{}`). Permissions belong in project or global settings.
- If you are prompted to approve a common command, note it for the user rather than accumulating in settings.local.json.
