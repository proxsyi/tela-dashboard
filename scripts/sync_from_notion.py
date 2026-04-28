#!/usr/bin/env python3
"""
sync_from_notion.py — Pull Notion public page content and sync dashboard files.

Architecture:
  Notion public page → this script → repo files → git commit → git push → GitHub Pages

The Notion page is fetched server-side (no CORS), code blocks are extracted,
and allowlisted files are written to the repo root.

Usage:
  python3 scripts/sync_from_notion.py [options]

Options:
  --source-url URL      Public Notion page URL (default: TELA_DASHBOARD_SOURCE_URL env or built-in default)
  --dry-run             Print what would change without writing files
  --no-git              Write files but skip git add/commit
  --push                After committing, run git push
  --message MSG         Custom commit message
  --verbose             Extra output
  --allow-missing       Do not exit with error if source page yields no blocks
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.request
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_SOURCE_URL = "https://cashmouzon.notion.site/tela-dashboard"

REPO_ROOT = Path(__file__).resolve().parent.parent

ALLOWED_FILES = {
    "config.json",
    "index.html",
    "style.css",
    "loader.js",
    "notion-source.js",
}

# Patterns that indicate a real secret value (not just docs mentioning them).
# These are checked against the raw extracted content.
SECRET_PATTERNS = [
    r'NOTION_TOKEN\s*[:=]\s*\S',
    r'api_key\s*[:=]\s*["\']?\w{16,}',
    r'(?i)\bsecret\s*[:=]\s*["\']?\w{16,}',
    r'(?i)\bpassword\s*[:=]\s*["\']?\S{8,}',
    r'(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}',
    r'(?i)private_key\s*[:=]',
    r'ssh-rsa\s+AAAA',
    r'(?i)protected[_\s]endpoint\s*[:=]',
]

# Notion serves static pre-rendered HTML to this specific bot UA pattern.
# The full SPA shell is served to custom UA strings, so this must stay as-is.
FETCH_USER_AGENT = "Mozilla/5.0 (compatible; bot)"

# ── Arg parsing ──────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source-url", default=None, help="Public Notion page URL")
    p.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    p.add_argument("--no-git", action="store_true", help="Write files but skip git")
    p.add_argument("--push", action="store_true", help="Push after commit")
    p.add_argument("--message", default="Sync dashboard from Notion", help="Commit message")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    p.add_argument("--allow-missing", action="store_true", help="OK if page yields no blocks")
    return p.parse_args()

# ── Logging ──────────────────────────────────────────────────────────────────

VERBOSE = False

def log(msg):
    print(msg)

def vlog(msg):
    if VERBOSE:
        print(f"  [verbose] {msg}")

def warn(msg):
    print(f"  [warn] {msg}", file=sys.stderr)

def err(msg):
    print(f"  [error] {msg}", file=sys.stderr)

# ── Fetch ────────────────────────────────────────────────────────────────────

def fetch_url(url):
    """Fetch a URL server-side with a bot User-Agent. Returns text or raises."""
    req = urllib.request.Request(url, headers={"User-Agent": FETCH_USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        charset = "utf-8"
        ct = resp.headers.get_content_charset()
        if ct:
            charset = ct
        return resp.read().decode(charset, errors="replace")

# ── HTML entity decode ───────────────────────────────────────────────────────

def decode_entities(text):
    return html.unescape(text)

def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text)

# ── Notion URL cleanup ───────────────────────────────────────────────────────

def clean_notion_urls(text):
    """Remove Notion-style <https://...> angle-bracket wrapping."""
    return re.sub(r"<(https?://[^>]+)>", r"\1", text)

# ── Extraction strategies ─────────────────────────────────────────────────────

def extract_heading_text(raw_heading_html):
    """Strip all tags from a heading element's inner HTML and decode entities."""
    return decode_entities(strip_tags(raw_heading_html)).strip()

def blocks_from_html(page_html):
    """
    Strategy 1: Parse Notion public page HTML.

    Notion's static/bot rendering exposes content as:
      <h2>filename.ext</h2>
      <pre><code class="language-X">...</code></pre>

    Or with no headings, just:
      <pre><code>...</code></pre>

    Returns a list of (heading_or_None, content_text) tuples.
    """
    results = []

    # Collect headings and pre blocks in document order, tracking positions.
    heading_re = re.compile(r"<h[1-6][^>]*>([\s\S]*?)</h[1-6]>", re.IGNORECASE)
    pre_re = re.compile(r"<pre[^>]*>([\s\S]*?)</pre>", re.IGNORECASE)

    headings = [(m.start(), extract_heading_text(m.group(1))) for m in heading_re.finditer(page_html)]
    pres = []
    for m in pre_re.finditer(page_html):
        inner = m.group(1)
        # Strip inner <code ...> tags but keep content
        content = decode_entities(strip_tags(inner)).strip()
        content = clean_notion_urls(content)
        if content:
            pres.append((m.start(), content))

    vlog(f"Strategy 1: found {len(headings)} headings, {len(pres)} pre blocks")

    if not pres:
        return results

    # Match each pre to the closest preceding heading.
    for pre_pos, pre_content in pres:
        # Find the last heading that appears before this pre block.
        preceding = [h for h in headings if h[0] < pre_pos]
        heading = preceding[-1][1] if preceding else None
        results.append((heading, pre_content))

    return results


def blocks_from_next_data(page_html):
    """
    Strategy 2: Extract from __NEXT_DATA__ if present (older Notion shared pages).
    """
    m = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>([\s\S]*?)</script>', page_html)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    # Look for code blocks in the recordMap
    record_map = (
        data.get("props", {})
            .get("pageProps", {})
            .get("recordMap", {})
    )
    if not record_map:
        vlog("Strategy 2: no recordMap found in __NEXT_DATA__")
        return []

    blocks = record_map.get("block", {})
    results = []
    heading_text = None

    # Sort blocks by their order — we don't have reliable order so try value keys.
    for block_id, block_data in blocks.items():
        bv = block_data.get("value", {})
        btype = bv.get("type", "")
        props = bv.get("properties", {})

        if btype in ("header", "sub_header", "sub_sub_header"):
            texts = props.get("title", [])
            heading_text = "".join(t[0] for t in texts if isinstance(t, list) and t)
        elif btype == "code":
            texts = props.get("title", [])
            code_text = "".join(t[0] for t in texts if isinstance(t, list) and t)
            if code_text:
                results.append((heading_text, clean_notion_urls(code_text)))
                heading_text = None

    vlog(f"Strategy 2: found {len(results)} code blocks from __NEXT_DATA__")
    return results


def blocks_from_markdown_fences(text):
    """
    Strategy 3: Extract from ``` fences in plain text / markdown export.
    """
    results = []
    lines = text.splitlines()
    i = 0
    heading_text = None
    while i < len(lines):
        line = lines[i].strip()
        # Heading patterns: ## filename or # filename
        hm = re.match(r"^#{1,3}\s+(\S+)", line)
        if hm:
            heading_text = hm.group(1)
            i += 1
            continue
        # Fence open
        fm = re.match(r"^```(\w*)", line)
        if fm:
            lang = fm.group(1)
            i += 1
            fence_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                fence_lines.append(lines[i])
                i += 1
            content = "\n".join(fence_lines).strip()
            if content:
                results.append((heading_text, clean_notion_urls(content)))
                heading_text = None
            i += 1
            continue
        i += 1

    vlog(f"Strategy 3: found {len(results)} fenced blocks")
    return results


def blocks_from_text_fallback(text):
    """
    Strategy 4: Last-resort — look for any JSON-looking object in the page text.
    """
    text = decode_entities(text)
    text = clean_notion_urls(text)

    # Try raw JSON parse of stripped text
    stripped = strip_tags(text).strip()
    # Find first { ... } block
    start = stripped.find("{")
    if start == -1:
        return []
    depth = 0
    for i in range(start, len(stripped)):
        c = stripped[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                candidate = stripped[start:i + 1]
                try:
                    json.loads(candidate)
                    vlog("Strategy 4: found JSON object in stripped text")
                    return [(None, candidate)]
                except json.JSONDecodeError:
                    break
    return []


def extract_all_blocks(page_html):
    """Run all extraction strategies in order, return first non-empty result."""
    for strategy_fn in [
        blocks_from_html,
        blocks_from_next_data,
        blocks_from_markdown_fences,
        blocks_from_text_fallback,
    ]:
        blocks = strategy_fn(page_html)
        if blocks:
            vlog(f"Extraction succeeded via {strategy_fn.__name__}")
            return blocks

    return []

# ── Heading → filename mapping ────────────────────────────────────────────────

def resolve_filename(heading, content, index):
    """
    Map a heading string to an allowed filename.
    If heading matches an allowed file, use it.
    If no heading and index == 0, default to config.json.
    """
    if heading:
        # Exact match
        if heading in ALLOWED_FILES:
            return heading
        # Lowercase match
        if heading.lower() in ALLOWED_FILES:
            return heading.lower()
        # Strip code fence language prefix (e.g. "json config.json")
        for allowed in ALLOWED_FILES:
            if heading.endswith(allowed):
                return allowed
        vlog(f"Heading '{heading}' does not match any allowed file — skipping")
        return None

    # No heading: first block defaults to config.json if content looks like JSON
    if index == 0:
        stripped = content.strip()
        if stripped.startswith("{"):
            return "config.json"
        vlog("First block has no heading and doesn't look like JSON — skipping")
    return None

# ── Validation ───────────────────────────────────────────────────────────────

def validate_config_json(content):
    """Parse and validate config.json content. Returns (obj, error_string)."""
    try:
        obj = json.loads(content)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"
    if not isinstance(obj, dict):
        return None, "config.json must be a JSON object"
    missing = [k for k in ("schemaVersion", "name", "status") if k not in obj]
    if missing:
        return None, f"config.json missing required keys: {missing}"
    progress = obj.get("progress")
    if progress is not None:
        try:
            float(progress)
        except (TypeError, ValueError):
            return None, f"config.json progress is not numeric: {progress!r}"
    return obj, None

# ── Safety scan ──────────────────────────────────────────────────────────────

def safety_scan(filename, content):
    """
    Return a list of issue strings if the content looks like it contains secrets.
    Empty list means safe.
    """
    issues = []
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, content):
            issues.append(f"Matched secret pattern: {pattern}")
    return issues

# ── File writing ──────────────────────────────────────────────────────────────

def read_existing(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

def write_file(path, content):
    """Write content to path, ensuring trailing newline."""
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")

# ── Git helpers ───────────────────────────────────────────────────────────────

def run_git(args, cwd=None):
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
    )
    return result

def git_add(paths):
    args = ["add", "--"] + [str(p.relative_to(REPO_ROOT)) for p in paths]
    r = run_git(args)
    if r.returncode != 0:
        warn(f"git add failed: {r.stderr.strip()}")
    return r.returncode == 0

def git_commit(message):
    r = run_git(["commit", "-m", message])
    if r.returncode != 0:
        if "nothing to commit" in r.stdout + r.stderr:
            return "nothing"
        warn(f"git commit failed: {r.stderr.strip()}")
        return "error"
    return "ok"

def git_push():
    r = run_git(["push"])
    if r.returncode != 0:
        err(f"git push failed: {r.stderr.strip()}")
        return False
    return True

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    args = parse_args()
    VERBOSE = args.verbose

    # Resolve source URL
    source_url = (
        args.source_url
        or os.environ.get("TELA_DASHBOARD_SOURCE_URL")
        or DEFAULT_SOURCE_URL
    )

    log(f"Tela Dashboard Sync")
    log(f"  Source : {source_url}")
    log(f"  Repo   : {REPO_ROOT}")
    if args.dry_run:
        log("  Mode   : dry-run (no files will be written)")
    elif args.no_git:
        log("  Mode   : write files, skip git")
    elif args.push:
        log("  Mode   : write, commit, push")
    else:
        log("  Mode   : write and commit (no push)")
    log("")

    # Fetch page
    log("Fetching source page…")
    try:
        page_html = fetch_url(source_url)
    except Exception as e:
        err(f"Failed to fetch source page: {e}")
        err("Check that the Notion page is public and the URL is correct.")
        sys.exit(1)

    vlog(f"Fetched {len(page_html)} bytes")

    # Extract blocks
    log("Extracting code blocks…")
    blocks = extract_all_blocks(page_html)

    if not blocks:
        msg = (
            "No extractable code blocks found in the Notion page.\n"
            "  The public Notion page may not yet contain any code blocks,\n"
            "  or the page structure has changed.\n"
            "  Add a code block to the Notion page, then re-run this script."
        )
        if args.allow_missing:
            warn(msg)
            log("--allow-missing set: exiting cleanly with no changes.")
            sys.exit(0)
        else:
            err(msg)
            sys.exit(1)

    log(f"Found {len(blocks)} code block(s)")

    # Map blocks to filenames
    file_contents = {}
    for i, (heading, content) in enumerate(blocks):
        fname = resolve_filename(heading, content, i)
        if fname is None:
            vlog(f"Block {i} (heading={heading!r}): no filename mapping, skipping")
            continue

        # Safety scan
        issues = safety_scan(fname, content)
        if issues:
            warn(f"Block for '{fname}' failed safety scan — skipping:")
            for issue in issues:
                warn(f"  {issue}")
            continue

        # Validate config.json
        if fname == "config.json":
            obj, verr = validate_config_json(content)
            if verr:
                warn(f"config.json validation failed: {verr} — skipping")
                continue
            # Re-serialise to ensure clean JSON with trailing newline
            content = json.dumps(obj, indent=2, ensure_ascii=False)

        file_contents[fname] = content
        log(f"  Block {i}: '{fname}' ({len(content)} chars, heading={heading!r})")

    if not file_contents:
        warn("No valid blocks mapped to allowed files.")
        if args.allow_missing:
            log("--allow-missing set: exiting cleanly.")
            sys.exit(0)
        sys.exit(1)

    # Diff against existing files
    changed_files = []
    unchanged_files = []
    for fname, content in file_contents.items():
        dest = REPO_ROOT / fname
        existing = read_existing(dest)
        normalised = (content + "\n") if not content.endswith("\n") else content
        if existing == normalised:
            unchanged_files.append(fname)
        else:
            changed_files.append((fname, content, dest))

    log("")
    if unchanged_files:
        log(f"No changes: {', '.join(unchanged_files)}")

    if not changed_files:
        log("All synced files are already up to date. Nothing to do.")
        sys.exit(0)

    log(f"Files to write ({len(changed_files)}):")
    for fname, content, dest in changed_files:
        existing = read_existing(dest)
        existing_lines = len(existing.splitlines()) if existing else 0
        new_lines = len(content.splitlines())
        action = "create" if existing is None else "update"
        log(f"  {action}: {fname}  ({existing_lines} → {new_lines} lines)")
        if args.verbose:
            # Print a small preview of content start
            preview = content[:300].replace("\n", "\n    ")
            log(f"    Preview:\n    {preview}{'…' if len(content) > 300 else ''}")

    if args.dry_run:
        log("")
        log("Dry run complete. No files written.")
        sys.exit(0)

    # Write files
    log("")
    log("Writing files…")
    written_paths = []
    for fname, content, dest in changed_files:
        write_file(dest, content)
        written_paths.append(dest)
        log(f"  Wrote: {fname}")

    if args.no_git:
        log("--no-git: skipping git operations.")
        log("Done.")
        sys.exit(0)

    # Git add + commit
    log("Running git add…")
    if not git_add(written_paths):
        err("git add failed; check output above.")
        sys.exit(1)

    log(f"Running git commit: \"{args.message}\"")
    result = git_commit(args.message)
    if result == "nothing":
        log("Nothing to commit (git index unchanged).")
    elif result == "error":
        err("git commit failed.")
        sys.exit(1)
    else:
        log("Committed.")

    if args.push:
        log("Running git push…")
        if not git_push():
            sys.exit(1)
        log("Pushed to origin.")

    log("")
    log("Sync complete.")


if __name__ == "__main__":
    main()
