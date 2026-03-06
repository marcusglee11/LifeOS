# COO Brief Template (Cron + Self-Orientation)

## Cron Template

Example:

```bash
openclaw cron add \
  --cron "*/20 8-20 * * *" \
  --tz "Australia/Sydney" \
  --announce \
  --message "COO heartbeat: orient, summarize status, and propose next dispatch action if needed."
```

## Session Orientation Protocol

Run in order at session start:

1. Read `SOUL.md` and `USER.md`.
2. Read daily logs: `memory/YYYY-MM-DD.md` (today + yesterday).
3. Read root memory: `MEMORY.md` (main session).
4. Query authoritative structured memory:
   `python3 /home/cabra/.openclaw/workspace/COO/memory/coo-memory.py query --namespace lifeos/dispatch`
5. Review repository operational state:
   - `config/tasks/backlog.yaml`
   - `artifacts/dispatch/inbox/`
   - `artifacts/dispatch/completed/`
   - `docs/11_admin/LIFEOS_STATE.md`
6. Use QMD or workspace recall search for supporting context when needed.

Fail-closed rule:
- If autonomy classification is unknown, escalate (L4).

## Brief Output Shape

Output status in `status_report.v1` format defined in `artifacts/coo/schemas.md`.

Minimum required sections:
- current health summary
- backlog/dispatch metrics
- pending escalations
- recommended next action
