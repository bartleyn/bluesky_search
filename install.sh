#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$HOME/.claude/tools"
SKILLS_DIR="$HOME/.claude/skills/bluesky-search"

echo "Installing bluesky-search Claude plugin..."

# Check dependencies
if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required." >&2
  exit 1
fi

if ! python3 -c "import atproto" &>/dev/null; then
  echo "Installing atproto Python package..."
  pip3 install --quiet atproto
fi

# Create directories
mkdir -p "$TOOLS_DIR" "$SKILLS_DIR"

# Symlink tool and skill
ln -sf "$REPO_DIR/tools/bluesky_search.py" "$TOOLS_DIR/bluesky_search.py"
chmod +x "$TOOLS_DIR/bluesky_search.py"
ln -sf "$REPO_DIR/skills/bluesky-search/SKILL.md" "$SKILLS_DIR/SKILL.md"

echo ""
echo "Installed. One more step — create your credentials file:"
echo ""
echo "  1. Go to Bluesky → Settings → Privacy and Security → App Passwords"
echo "  2. Create a new app password (name it 'claude-tool' or similar)"
echo "  3. Run:"
echo ""
echo "     cat > $TOOLS_DIR/.bluesky_creds << 'EOF'"
echo "     ATMOSPHERE_ACCOUNT=you.bsky.social"
echo "     BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx"
echo "     EOF"
echo "     chmod 600 $TOOLS_DIR/.bluesky_creds"
echo ""
echo "Then use /bluesky-search in Claude Code, or run:"
echo "  python3 ~/.claude/tools/bluesky_search.py search \"your query\""
