# Tela Hub Dashboard

A custom static dashboard for Tela Hub, hosted on GitHub Pages and embeddable in Notion via iframe.

No build step. No backend. No secrets. Pure HTML/CSS/JS.

---

## Local test

```bash
python3 -m http.server 4173
```

Then open: http://localhost:4173

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
  -f source.branch=main \
  -f source.path=/
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

## Passing a public JSON config URL

Append `?config=<url>` to the dashboard URL:

```
https://proxsyi.github.io/tela-dashboard/?config=https://example.com/tela-config.json
```

The JSON must be a public CORS-accessible URL that returns a config object matching the schema in `loader.js`.

---

## Passing a public Notion source URL

Append `?notionSource=<url>` to the dashboard URL:

```
https://proxsyi.github.io/tela-dashboard/?notionSource=https://www.notion.so/your-public-page
```

The dashboard will attempt to fetch the page and extract the first JSON config block. Direct Notion fetches are often CORS-blocked — if so, export or mirror the config as a plain JSON file instead.

---

## Embedding in Notion

In a Notion page, use `/embed` and paste the GitHub Pages URL:

```
https://proxsyi.github.io/tela-dashboard/
```

Set the embed height to your preference (600–900px recommended).

---

## Security rules

- No tokens or secrets in this repo.
- No private machine details.
- No protected or internal endpoint URLs.
- No live system controls in v1.
- No credentials of any kind.
- Everything in this repo is public-safe.

---

## Manual steps remaining

1. **Publish the public-safe Notion source page** — review the config content, then make the Notion page public before passing its URL as `?notionSource=`.
2. **Test whether direct Notion fetch works** — Notion often blocks CORS. If blocked, host the config JSON at a public URL instead.
3. **If CORS blocks Notion fetch** — use a public static JSON URL (`?config=`), or set up a tiny public proxy later.
4. **Paste the GitHub Pages URL into Tela Hub** — add the embed block on the Tela Hub Notion page.
5. **Report back to Notion project page** — paste the repo URL and Pages URL so the project record is up to date.

---

## URLs

- Repo: https://github.com/proxsyi/tela-dashboard
- Pages: https://proxsyi.github.io/tela-dashboard/
