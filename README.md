# Tela Hub Dashboard

A custom static dashboard for Tela Hub, hosted on GitHub Pages and embeddable in Notion via iframe.

No build step. No backend. No secrets. Pure HTML/CSS/JS.

---

## Architecture

```
Notion public page  →  sync script (Air)  →  repo files  →  git push  →  GitHub Pages  →  Tela Hub embed
```

**Notion is the source of truth** for dashboard config (and optionally other files).  
A sync script runs locally on Cash's MacBook Air, fetches the public Notion page server-side,
extracts code blocks, and pushes changes to GitHub.  
The browser reads `config.json` from GitHub Pages — no Notion token, no CORS issues.

### Config priority (in the browser)

1. `?config=<url>` query param — override with any public JSON URL
2. `./config.json` — synced from Notion by the sync script (**default path**)
3. Bundled fallback config in `loader.js` — used if config.json is absent

---

## Sync script

See [`scripts/README.md`](scripts/README.md) for full documentation.

**Quick start:**

```bash
# Dry run — see what would change
python3 scripts/sync_from_notion.py --dry-run --verbose

# Write config.json (no git)
python3 scripts/sync_from_notion.py --no-git

# Write, commit, and push
python3 scripts/sync_from_notion.py --push
```

The sync script fetches:
```
https://cashmouzon.notion.site/tela-dashboard
```

---

## Local test

```bash
python3 -m http.server 4174
```

Open: http://localhost:4174  
The dashboard should load `config.json` and show "Notion source config is working."

---

## GitHub repo creation & deploy

First time only:

```bash
gh repo create proxsyi/tela-dashboard --public --source=. --remote=origin --push
```

If the repo already exists:

```bash
git remote remove origin
git remote add origin https://github.com/proxsyi/tela-dashboard.git
git push -u origin main
```

---

## Enable GitHub Pages

```bash
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  /repos/proxsyi/tela-dashboard/pages \
  --input - <<'EOF'
{"source":{"branch":"main","path":"/"}}
EOF
```

If Pages already exists (update):

```bash
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/proxsyi/tela-dashboard/pages \
  -f source.branch=main \
  -f source.path=/
```

Check Pages URL:

```bash
gh api /repos/proxsyi/tela-dashboard/pages --jq .html_url
```

---

## Embedding in Notion

In a Notion page, use `/embed` and paste the GitHub Pages URL:

```
https://proxsyi.github.io/tela-dashboard/
```

Set the embed height to 700–900px.

---

## Passing a public JSON config URL (override)

Append `?config=<url>` to override config from any public JSON source:

```
https://proxsyi.github.io/tela-dashboard/?config=https://example.com/tela-config.json
```

---

## ?notionSource= (experimental, usually CORS-blocked)

The browser can try to fetch a Notion page directly:

```
https://proxsyi.github.io/tela-dashboard/?notionSource=https://cashmouzon.notion.site/tela-dashboard
```

This is blocked by CORS in most browsers. Use the sync script instead.  
`?notionSource=` remains supported in the code for testing and future use.

---

## Security rules

- No tokens or secrets in this repo.
- No private machine details.
- No protected or internal endpoint URLs.
- No live system controls in v1.
- No credentials of any kind.
- Everything in this repo is public-safe.

---

## URLs

- Repo: https://github.com/proxsyi/tela-dashboard
- Pages: https://proxsyi.github.io/tela-dashboard/
- Notion source: https://cashmouzon.notion.site/tela-dashboard
