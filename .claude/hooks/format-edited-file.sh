#!/usr/bin/env bash
# Description: PostToolUse hook that formats the just-edited file with prettier when the type is supported.
# Description: Reads the tool JSON on stdin (tool_input.file_path); non-blocking, never fails an edit.

# The edited path arrives in the PostToolUse JSON on stdin, not an env var.
# Edit and Write both put it at tool_input.file_path.
FILE_PATH="$(jq -r '.tool_input.file_path // empty' 2>/dev/null)"

# No path, or the file is gone: nothing to format, let the edit stand.
[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

# Only invoke prettier on types it actually formats. Anything else (e.g. .py)
# exits quietly so we do not spawn a pointless process on every backend edit.
case "$FILE_PATH" in
  *.js|*.jsx|*.ts|*.tsx|*.vue|*.json|*.css|*.scss|*.html|*.md|*.yaml|*.yml) ;;
  *) exit 0 ;;
esac

# Prefer a locally installed prettier (fast, version-pinned); fall back to npx.
# Derive the project dir from the script location so this also works when run by hand.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
if [ -x "$PROJECT_DIR/client/node_modules/.bin/prettier" ]; then
  PRETTIER=("$PROJECT_DIR/client/node_modules/.bin/prettier")
else
  PRETTIER=(npx -y prettier)
fi

# Format in place. Report the outcome on stderr (surfaces in the transcript) rather
# than swallowing it silently, so a broken formatter is visible instead of a no-op.
if "${PRETTIER[@]}" --write "$FILE_PATH" >/dev/null 2>&1; then
  echo "prettier: formatted $FILE_PATH" >&2
else
  echo "prettier: skipped $FILE_PATH (prettier unavailable or unsupported)" >&2
fi

# Always succeed: formatting is a convenience, it must never block an edit.
exit 0
