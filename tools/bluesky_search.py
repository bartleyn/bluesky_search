#!/usr/bin/env python3
"""Bluesky thread/conversation search tool using AT Protocol SDK."""

import os
import re
import stat
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Strips ANSI/VT escapes, 8-bit C1 controls, and Unicode bidi override characters
# from untrusted content before terminal output.
_ANSI_ESCAPE = re.compile(
    r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))'  # ESC sequences
    r'|\x9b[0-?]*[ -/]*[@-~]'   # 8-bit CSI (equivalent to ESC [)
    r'|[\x80-\x9f]'             # remaining C1 control codes
    r'|[\x07\x08\x0c]'          # BEL, BS, FF
    r'|[‪-‮⁦-⁩‏؜]'  # Unicode bidi/RTL overrides
)

try:
    from atproto import Client
    from atproto_client.exceptions import AtProtocolError
except ImportError:
    print("Missing dependency: pip3 install atproto", file=sys.stderr)
    sys.exit(1)

TOOLS_DIR = Path.home() / ".claude" / "tools"
SESSION_FILE = TOOLS_DIR / ".bluesky_session"
CREDS_FILE = Path(os.environ.get("BLUESKY_CREDS_FILE", TOOLS_DIR / ".bluesky_creds"))

_SAFE_HANDLE = re.compile(r'^[a-zA-Z0-9._:-]+$')
_SAFE_RKEY  = re.compile(r'^[a-zA-Z0-9._~-]+$')


def _read_creds():
    """Read atmo_acct + app password from the credentials file."""
    if not CREDS_FILE.exists():
        print(
            f"Credentials file not found: {CREDS_FILE}\n"
            "Create it with:\n"
            "  ATMOSPHERE_ACCOUNT=you.bsky.social\n"
            "  BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx\n"
            "Then: chmod 600 ~/.claude/tools/.bluesky_creds\n\n"
            "Generate an app password at: Bluesky → Settings → Privacy and Security → App Passwords",
            file=sys.stderr,
        )
        sys.exit(1)
    st = CREDS_FILE.stat()
    file_mode = stat.S_IMODE(st.st_mode)
    if file_mode & 0o077:
        print(
            f"Credentials file {CREDS_FILE} has unsafe permissions ({oct(file_mode)}).\n"
            "Run: chmod 600 ~/.claude/tools/.bluesky_creds",
            file=sys.stderr,
        )
        sys.exit(1)
    if st.st_uid != os.getuid():
        print(
            f"Credentials file {CREDS_FILE} is not owned by the current user.",
            file=sys.stderr,
        )
        sys.exit(1)
    creds = {}
    for line in CREDS_FILE.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            creds[k.strip()] = v.strip()
    handle = creds.get("ATMOSPHERE_ACCOUNT")
    password = creds.get("BLUESKY_APP_PASSWORD")
    if not handle or not password:
        print("Credentials file must contain ATMOSPHERE_ACCOUNT and BLUESKY_APP_PASSWORD", file=sys.stderr)
        sys.exit(1)
    return handle, password


def load_client():
    client = Client()
    if SESSION_FILE.exists():
        try:
            st = SESSION_FILE.stat()
            if stat.S_IMODE(st.st_mode) & 0o077 or st.st_uid != os.getuid():
                print("Warning: session file has unsafe permissions, ignoring it.", file=sys.stderr)
                SESSION_FILE.unlink(missing_ok=True)
                raise AtProtocolError("bad session file permissions")
            session_str = SESSION_FILE.read_text().strip()
            client.login(session_string=session_str)
            _save_session(client)
            return client
        except AtProtocolError:
            SESSION_FILE.unlink(missing_ok=True)
        except Exception as e:
            print(f"Warning: could not resume session ({e}), re-authenticating.", file=sys.stderr)
            SESSION_FILE.unlink(missing_ok=True)

    handle, password = _read_creds()
    try:
        client.login(login=handle, password=password)
        _save_session(client)
    except AtProtocolError as e:
        print(f"Login failed: {e}", file=sys.stderr)
        sys.exit(1)
    return client


def _save_session(client):
    session_str = client.export_session_string()
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Write with O_CREAT|O_WRONLY|O_TRUNC and mode 0o600 atomically — avoids
    # the race window between write_text() and chmod().
    fd = os.open(SESSION_FILE, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)  # enforce even if file pre-existed with wrong perms
        os.write(fd, session_str.encode())
    finally:
        os.close(fd)


def fmt_time(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return _sanitize(iso)  # sanitize raw fallback before terminal output


def _sanitize(s):
    """Strip ANSI/VT escape sequences from untrusted content before terminal output."""
    return _ANSI_ESCAPE.sub("", s)


def fmt_post(post, brief=False):
    """Format the post for the CLI output"""
    author = post.author
    atmo_acct = _sanitize(author.handle or "")
    display = _sanitize(author.display_name or "")
    record = post.record
    text = _sanitize(getattr(record, "text", "") or "")
    ts = fmt_time(getattr(record, "created_at", "") or "")
    uri = _sanitize(post.uri or "")
    rkey = uri.split("/")[-1] if uri else ""
    if rkey and not _SAFE_RKEY.match(rkey):
        rkey = ""
    url = f"https://bsky.app/profile/{atmo_acct}/post/{rkey}" if rkey else uri

    name_line = f"{display} (@{atmo_acct})" if display else f"@{atmo_acct}"

    if brief:
        first_line = text.splitlines()[0] if text else ""
        if len(first_line) > 80:
            first_line = first_line[:77] + "..."
        return f"{name_line}  •  {ts}\n  {first_line}\n  {url}"

    likes = post.like_count or 0
    replies = post.reply_count or 0
    reposts = post.repost_count or 0

    return "\n".join([
        f"{'─' * 60}",
        f"{name_line}  •  {ts}",
        f"  {text.replace(chr(10), chr(10) + '  ')}",
        f"  ♥ {likes}  ↩ {replies}  ↗ {reposts}",
        f"  {url}",
    ])


_AT_URI = re.compile(r'^at://([a-zA-Z0-9._:-]+)/([a-zA-Z0-9.]+)/([a-zA-Z0-9._~-]+)$')

def url_to_at_uri(url):
    """Validate and normalize URLs/at URIs"""
    if url.startswith("at://"):
        if not _AT_URI.match(url):
            print(f"Malformed AT URI: {url}", file=sys.stderr)
            sys.exit(1)
        return url
    parts = url.rstrip("/").split("/")
    try:
        prof_idx = parts.index("profile")
        post_idx = parts.index("post")
        atmo_acct = parts[prof_idx + 1]
        rkey = parts[post_idx + 1]
    except (ValueError, IndexError):
        print(f"Cannot parse URL: {url}", file=sys.stderr)
        sys.exit(1)
    if not _SAFE_HANDLE.match(atmo_acct) or not _SAFE_RKEY.match(rkey):
        print(f"URL contains unexpected characters: {url}", file=sys.stderr)
        sys.exit(1)
    return f"at://{atmo_acct}/app.bsky.feed.post/{rkey}"


def print_thread_node(node, indent=0, max_depth=10, brief=False):
    if indent > max_depth or node is None:
        return
    ntype = getattr(node, "py_type", "") or ""
    if "threadViewPost" in ntype:
        post = node.post
        pad = "  " * indent
        lines = fmt_post(post, brief=brief).splitlines()
        for line in lines:
            print(pad + line)
        print()
        for reply in (node.replies or []):
            print_thread_node(reply, indent + 1, max_depth, brief=brief)
    elif "notFoundPost" in ntype:
        print(f"{'  ' * indent}[post not found]")
    elif "blockedPost" in ntype:
        print(f"{'  ' * indent}[blocked post]")


def _expand_date(s, end_of_day=False):
    """Expand YYYY-MM-DD to a full AT Protocol datetime string."""
    if s and re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return f"{s}T{'23:59:59' if end_of_day else '00:00:00'}.000Z"
    return s


def cmd_search(args):
    client = load_client()
    params = dict(q=args.query, limit=args.limit, sort=args.sort)
    if args.since:
        params["since"] = _expand_date(args.since)
    if args.until:
        params["until"] = _expand_date(args.until, end_of_day=True)
    if args.author:
        params["author"] = args.author
    if args.lang:
        params["lang"] = args.lang

    print(f"Searching: \"{args.query}\"  sort={args.sort}  limit={args.limit}\n")
    try:
        resp = client.app.bsky.feed.search_posts(params)
    except AtProtocolError as e:
        print(f"Search failed: {e}", file=sys.stderr)
        sys.exit(1)

    posts = resp.posts or []
    total = getattr(resp, "hits_total", None)
    if total is not None:
        print(f"Total matching posts: {total}")
    if not posts:
        print("No results.")
        return
    print(f"Showing {len(posts)} result(s):\n")
    for post in posts:
        print(fmt_post(post, brief=args.brief))
        print()
    _maybe_logout(args)


def cmd_thread(args):
    client = load_client()
    uri = url_to_at_uri(args.url)
    print(f"Fetching thread: {uri}\n")
    try:
        resp = client.app.bsky.feed.get_post_thread(
            {"uri": uri, "depth": args.depth, "parent_height": args.parents}
        )
    except AtProtocolError as e:
        print(f"Thread fetch failed: {e}", file=sys.stderr)
        sys.exit(1)

    print_thread_node(resp.thread, max_depth=args.depth, brief=args.brief)
    _maybe_logout(args)


def cmd_feed(args):
    client = load_client()
    print(f"Posts by @{args.account}  limit={args.limit}\n")
    try:
        resp = client.app.bsky.feed.get_author_feed(
            {"actor": args.account, "limit": args.limit}
        )
    except AtProtocolError as e:
        print(f"Feed fetch failed: {e}", file=sys.stderr)
        sys.exit(1)

    for item in (resp.feed or []):
        reason = item.reason
        if reason and "reasonRepost" in (getattr(reason, "py_type", "") or ""):
            print("  [repost]")
        print(fmt_post(item.post, brief=args.brief))
        print()
    _maybe_logout(args)


def _maybe_logout(args):
    if not getattr(args, "logout_after", False):
        return
    ans = input("\nDone with Bluesky? Clear session token? [y/N] ").strip().lower()
    if ans == "y":
        SESSION_FILE.unlink(missing_ok=True)
        print("Session cleared.")


def cmd_logout(_args):
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
        print("Session cleared.")
    else:
        print("No cached session.")


def main():
    parser = argparse.ArgumentParser(
        description="Search Bluesky posts and fetch threads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bluesky_search.py search "claude ai"
  bluesky_search.py search "open source" --sort top --limit 20
  bluesky_search.py search "rust" --author nytimes.com --since 2026-01-01
  bluesky_search.py thread https://bsky.app/profile/user.bsky.social/post/3jxxxxxx
  bluesky_search.py feed atproto.com --limit 15  # ATMOSPHERE_ACCOUNT
  bluesky_search.py logout
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("search", help="Full-text search for posts")
    sp.add_argument("query")
    sp.add_argument("--limit", type=lambda x: min(max(1, int(x)), 100), default=10, metavar="N")
    sp.add_argument("--sort", choices=["latest", "top"], default="latest")
    sp.add_argument("--author", metavar="HANDLE")
    sp.add_argument("--since", metavar="DATE", help="ISO 8601, e.g. 2026-01-01")
    sp.add_argument("--until", metavar="DATE")
    sp.add_argument("--lang", metavar="LANG")
    sp.add_argument("--brief", action="store_true", help="Compact output (one line per post)")
    sp.add_argument("--logout-after", action="store_true", help="Prompt to clear session when done")
    sp.set_defaults(func=cmd_search)

    tp = sub.add_parser("thread", help="Fetch a full thread by URL or AT URI")
    tp.add_argument("url")
    tp.add_argument("--depth", type=lambda x: min(max(1, int(x)), 20), default=8)
    tp.add_argument("--parents", type=lambda x: min(max(1, int(x)), 20), default=10)
    tp.add_argument("--brief", action="store_true", help="Compact output (one line per post)")
    tp.add_argument("--logout-after", action="store_true", help="Prompt to clear session when done")
    tp.set_defaults(func=cmd_thread)

    fp = sub.add_parser("feed", help="Show recent posts from a user")
    fp.add_argument("account", metavar="ATMOSPHERE_ACCOUNT")
    fp.add_argument("--limit", type=lambda x: min(max(1, int(x)), 100), default=10, metavar="N")
    fp.add_argument("--brief", action="store_true", help="Compact output (one line per post)")
    fp.add_argument("--logout-after", action="store_true", help="Prompt to clear session when done")
    fp.set_defaults(func=cmd_feed)

    lp = sub.add_parser("logout", help="Clear cached session")
    lp.set_defaults(func=cmd_logout)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
