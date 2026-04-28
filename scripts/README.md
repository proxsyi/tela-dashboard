# Scripts — Tela Dashboard Sync

## How it works

```
Notion public page  →  sync_from_notion.py  →  repo files  →  git push  →  GitHub Pages
```

`sync_from_notion.py` fetches the public Notion page server-side (no CORS, no token),
extracts named code blocks, safety-scans each one, and writes only allowlisted files.

The script runs on Cash's MacBook Air (or any machine with Python 3 and git).
The browser never fetches Notion — it reads `config.json` from GitHub Pages.

---

## Notion page format

The source page lives at:

```
https://cashmouzon.notion.site/tela-dashboard
```

**Single-file mode** (current default):  
Put one JSON code block on the page. The script defaults it to `config.json`.

**Multi-file mode** (future):  
Add a heading immediately before each code block. The heading must exactly match an allowed filename:

```
## config.json

{ ... }

## loader.js

(function() { ... })();
```

Allowed filenames:
- `config.json`
- `index.html`
- `style.css`
- `loader.js`
- `notion-source.js`

Files NOT in the allowlist are never written by this script, no matter what headings are present.

---

## Commands

**Dry run (inspect without writing):**
```bash
python3 scripts/sync_from_notion.py --dry-run --verbose
```

**Write files only (no git):**
```bash
python3 scripts/sync_from_notion.py --no-git
```

**Write and commit (no push):**
```bash
python3 scripts/sync_from_notion.py
```

**Write, commit, and push:**
```bash
python3 scripts/sync_from_notion.py --push
```

**Custom source URL:**
```bash
TELA_DASHBOARD_SOURCE_URL="https://cashmouzon.notion.site/tela-dashboard" \
  python3 scripts/sync_from_notion.py --push
```

**Run via convenience shell script:**
```bash
bash scripts/run_sync.sh
```

---

## Automating with launchd (MacBook Air)

To run every 10 minutes on macOS, create a launchd plist at
`~/Library/LaunchAgents/com.tela.dashboard.sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.tela.dashboard.sync</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/path/to/tela-dashboard/scripts/sync_from_notion.py</string>
    <string>--push</string>
  </array>
  <key>StartInterval</key>
  <integer>600</integer>
  <key>RunAtLoad</key>
  <false/>
  <key>StandardOutPath</key>
  <string>/tmp/tela-sync.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/tela-sync-err.log</string>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.tela.dashboard.sync.plist
```

Replace `/path/to/tela-dashboard` with the actual repo path.

---

## CLI flags reference

| Flag | Default | Description |
|---|---|---|
| `--source-url URL` | env or built-in default | Override Notion page URL |
| `--dry-run` | off | Print what would change, write nothing |
| `--no-git` | off | Write files, skip git add/commit/push |
| `--push` | off | Push to origin after committing |
| `--message MSG` | `"Sync dashboard from Notion"` | Custom commit message |
| `--verbose` | off | Extra output (extraction details, previews) |
| `--allow-missing` | off | Exit cleanly (not as error) when page has no blocks |

---

## Security rules

- **No tokens.** The script fetches a public URL only.
- **No secrets.** The source Notion page must stay public-safe.
- **No private machine details** in config.
- **No protected endpoints** in config.
- **Safety scan**: content is rejected if it contains patterns like
  `NOTION_TOKEN=`, `api_key=<longvalue>`, `ssh-rsa AAAA`, etc.
- **Allowlist**: only the five listed filenames can ever be written.
- **Never overwrites** `README.md`, `.gitignore`, `scripts/*`, or anything outside the repo.
