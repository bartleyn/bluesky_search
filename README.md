# bluesky-search

A Claude Code plugin for searching Bluesky posts, threads, and feeds via the AT Protocol.

## Install

```bash
git clone https://github.com/bartleyn/bluesky_search ~/.claude/plugins/bluesky-search
~/.claude/plugins/bluesky-search/install.sh
```

## Setup

1. Create an app password: **Bluesky → Settings → Privacy and Security → App Passwords**
2. Create a credentials file:
   ```bash
   cat > ~/.claude/tools/.bluesky_creds << 'EOF'
   ATMOSPHERE_ACCOUNT=you.bsky.social
   BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
   EOF
   chmod 600 ~/.claude/tools/.bluesky_creds
   ```

## Usage

Once installed, use `/bluesky-search` in Claude Code, or run the script directly:

```bash
# Search posts
python3 ~/.claude/tools/bluesky_search.py search "query" [--sort top] [--limit 20]
python3 ~/.claude/tools/bluesky_search.py search "query" --author handle.bsky.social --since 2026-01-01

# Fetch a full thread
python3 ~/.claude/tools/bluesky_search.py thread https://bsky.app/profile/handle/post/rkey

# Browse an account's recent posts
python3 ~/.claude/tools/bluesky_search.py feed ATMOSPHERE_ACCOUNT [--limit 15]

# Clear cached session
python3 ~/.claude/tools/bluesky_search.py logout
```

## Security notes

- Your app password is stored in `~/.claude/tools/.bluesky_creds` (mode 600). The script refuses to run if permissions are weaker than that.
- After first login, only a JWT session token is cached in `~/.claude/tools/.bluesky_session` (also mode 600).
- App passwords are scoped — they cannot change your email, password, or account settings, and can be revoked individually from Bluesky settings.
- Use `BLUESKY_CREDS_FILE=/path/to/creds` to override the default credentials path.

## Requirements

- Python 3.9+
- `atproto` (`pip3 install atproto`)
