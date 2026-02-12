# COO Windows Launchers

These launchers provide pin-friendly Windows entrypoints for the COO UX.

Files:

- `COO_TUI.cmd`: launch `coo tui` inside WSL Ubuntu.
- `COO_APP.cmd`: launch `coo app` inside WSL Ubuntu.
- `COO_STOP.cmd`: launch `coo stop` inside WSL Ubuntu.

Pin instructions:

1. Navigate to `tools/windows/` in File Explorer.
2. Right-click a `.cmd` file and create a shortcut.
3. Pin the shortcut to Start or Taskbar.

Security notes:

- Launchers never include tokens or secrets.
- Slack tokens/signing secrets must be supplied as environment variables at runtime only.

