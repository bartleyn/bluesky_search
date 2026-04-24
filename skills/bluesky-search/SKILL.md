---
name: bluesky-search
description: Search Bluesky posts and fetch threads/conversations using the AT Protocol. Use when the user wants to find posts, read a thread, or browse a user's feed on Bluesky.
license: MIT
---

# Bluesky Search

Search for Bluesky posts and threads using the script at `~/.claude/tools/bluesky_search.py`.

## Setup (first time)

1. Create an app password: Bluesky → Settings → Privacy and Security → App Passwords
2. Create `~/.claude/tools/.bluesky_creds` with:
   ```
   BLUESKY_HANDLE=you.bsky.social
   BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
   ```
3. Run `chmod 600 ~/.claude/tools/.bluesky_creds`

The script reads credentials from that file automatically.

## Commands

```bash
# Search posts (latest by default, or --sort top)
python3 ~/.claude/tools/bluesky_search.py search "query" [--sort top] [--limit 20] [--author handle] [--since 2026-01-01] [--lang en]

# Fetch a full thread by URL or AT URI
python3 ~/.claude/tools/bluesky_search.py thread <url_or_at_uri> [--depth 8]

# Browse a user's recent posts
python3 ~/.claude/tools/bluesky_search.py feed <handle> [--limit 15]

# Clear cached session
python3 ~/.claude/tools/bluesky_search.py logout
```

## Usage

When the user invokes `/bluesky-search`, ask what they want to find if not already specified, then run the appropriate command via Bash and present the results cleanly. For threads, summarize the conversation structure after showing the raw output if it is long.

## Token efficiency

Be conservative with fetches to avoid bloating context:
- Default `--limit` to 10 or fewer unless the user asks for more
- For threads (`thread` command), always fetch full output — the user is reading the whole conversation, so `--brief` would cut off content they need. Never use `--brief` for threads.
- For `search` and `feed`, ask the user before defaulting to `--brief`: "Want brief output to save context, or full posts?" — use `--brief` only if they say yes or if they've already indicated they want to scan rather than read.
- For threads, `--depth 4` is usually enough for an overview; only go deeper if the user asks
- Prefer one focused query over multiple broad ones

## Session hygiene

When the conversation about Bluesky seems to be wrapping up, ask the user: "Done with Bluesky for now? I can clear the session token." If they confirm, run:
```bash
python3 ~/.claude/tools/bluesky_search.py logout
```
Do not clear the session mid-conversation without asking.
