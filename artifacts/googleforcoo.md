Current state is simple and bad:
- Hermes: no `google_token.json`, no `google_client_secret.json`
- OpenClaw: no `google_token.json`, no `google_client_secret.json`
- `gws` is not installed
- I also found and patched a bug in the Hermes `google-workspace` skill: its setup commands were missing `PYTHONPATH`, so the documented flow was broken from arbitrary directories

My recommendation:
Use one shared Google account and one shared credential bundle now, then symlink it into both COO environments.
Don’t do two unrelated auth snowflakes.

Clean near-term model

Common surface
- one shared Google Drive folder for COO/advisory artefacts
- one Google Cloud project
- one OAuth desktop client
- one shared credential directory on this machine, e.g.
  - `/home/cabra/.config/lifeos-google/`
    - `google_client_secret.json`
    - `google_token.json`

Consumers
- Hermes reads via symlinks from:
  - `~/.hermes/google_client_secret.json`
  - `~/.hermes/google_token.json`
- OpenClaw reads via symlinks from:
  - `~/.openclaw/google_client_secret.json`
  - `~/.openclaw/google_token.json`

That gives both COOs the same surface and avoids auth drift.

Exact setup sequence

Phase 1: create the Google side once
1. Go to:
   - https://console.cloud.google.com/apis/credentials
2. Create or pick a Google Cloud project for LifeOS
3. Enable these APIs:
   - Google Drive API
   - Google Docs API
   - Google Sheets API
   - Gmail API if you want mail too
   - People API if contacts matter
4. Create credentials:
   - Credentials -> Create Credentials -> OAuth client ID
   - Application type: Desktop app
5. Download the client secret JSON

Phase 2: create the shared local credential home
Run:
```bash
mkdir -p /home/cabra/.config/lifeos-google
```

Then put the downloaded JSON there as:
- `/home/cabra/.config/lifeos-google/google_client_secret.json`

Phase 3: install the runtime dependency once
Run:
```bash
npm install -g @googleworkspace/cli
```

Verify:
```bash
gws --version
```

Phase 4: wire Hermes to the shared credentials
Run:
```bash
ln -snf /home/cabra/.config/lifeos-google/google_client_secret.json /home/cabra/.hermes/google_client_secret.json
ln -snf /home/cabra/.config/lifeos-google/google_token.json /home/cabra/.hermes/google_token.json
```

The token symlink will be broken until auth completes. That’s fine.

Phase 5: do the initial OAuth flow via Hermes
Use this exact shell setup:
```bash
export HERMES_HOME="$HOME/.hermes"
export PYTHONPATH="$HERMES_HOME/hermes-agent${PYTHONPATH:+:$PYTHONPATH}"
GSETUP="python3 $HERMES_HOME/skills/productivity/google-workspace/scripts/setup.py"
```

Check state:
```bash
$GSETUP --check
```

Register the client secret if needed:
```bash
$GSETUP --client-secret /home/cabra/.config/lifeos-google/google_client_secret.json
```

Generate auth URL:
```bash
$GSETUP --auth-url
```

Then:
- open the URL in your browser
- approve access
- copy back the full redirect URL or code

Exchange it:
```bash
$GSETUP --auth-code "PASTE_THE_URL_OR_CODE_HERE"
```

Verify:
```bash
$GSETUP --check
```

If this works, `/home/cabra/.config/lifeos-google/google_token.json` now exists and Hermes is live.

Phase 6: wire OpenClaw to the same shared credentials
Run:
```bash
mkdir -p /home/cabra/.openclaw
ln -snf /home/cabra/.config/lifeos-google/google_client_secret.json /home/cabra/.openclaw/google_client_secret.json
ln -snf /home/cabra/.config/lifeos-google/google_token.json /home/cabra/.openclaw/google_token.json
```

Phase 7: give OpenClaw a minimal convention
OpenClaw needs a stable rule like:
- Google creds live at `~/.openclaw/google_client_secret.json` and `~/.openclaw/google_token.json`
- these may be symlinks to the shared LifeOS credential bundle
- Drive/Docs access uses the same Google account until per-agent identities exist

If OpenClaw already has a Google integration script, point it there.
If not, the fastest thing is to mirror the Hermes bridge pattern instead of inventing new magic.

Recommended operating rule
Near-term:
- one Google identity
- one shared token bundle
- both COOs get read/write access to the same Drive/Docs surfaces

Medium-term:
- separate agent identities or service accounts
- bounded folder permissions
- better auditability
- no shared token

What not to do
- Don’t set up Hermes and OpenClaw with different ad hoc Google projects
- Don’t make each one use a different Drive root
- Don’t leave one on manual-export mode and the other on live Drive
That’s how you get two “common surfaces” that aren’t common.

What I’d do next
1. You get/download the OAuth desktop client JSON
2. We store it in `/home/cabra/.config/lifeos-google/google_client_secret.json`
3. I walk you through the Hermes auth URL/code exchange
4. Then we wire OpenClaw to the same credential bundle

If you want, next message I can give you:
- the exact commands only, no explanation
or
- an OpenClaw-side mini spec for “Google Drive credential contract v1” you can paste into its repo.