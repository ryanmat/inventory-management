#!/usr/bin/env bash
# Description: First-pass scanner for Vue component optimization smells.
# Description: Surfaces greppable candidates only; the model verifies each in context and reasons about the rest.
# grep exits non-zero on no-match by design, so this script does not use `set -e`.
set -u

DIR="${1:-client/src}"

if [ ! -d "$DIR" ]; then
  echo "Directory not found: $DIR" >&2
  echo "Usage: bash scan.sh [path-to-src]  (default: client/src)" >&2
  exit 1
fi

echo "=== Vue optimizer scan: $DIR ==="
echo

# 1. v-for using the array index as :key. Index keys make Vue reuse the wrong
#    DOM nodes when a list changes. These are near-always worth fixing.
echo "--- v-for index keys (use a stable unique id instead) ---"
if grep -rnE ':key="(index|idx|i)"' --include='*.vue' "$DIR"; then
  :
else
  echo "(none found)"
fi
echo

# 2. Helper functions/consts defined in more than one .vue file. Strong
#    candidates for extraction to utils/ or a composable -- verify the bodies
#    actually match before recommending it.
echo "--- helper names defined in multiple components (extraction candidates) ---"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
while IFS= read -r f; do
  { grep -oE 'const [a-zA-Z_][a-zA-Z0-9_]* = (async )?\(|function [a-zA-Z_][a-zA-Z0-9_]*\(' "$f" 2>/dev/null || true; } \
    | sed -E 's/^const ([a-zA-Z_][a-zA-Z0-9_]*).*/\1/; s/^function ([a-zA-Z_][a-zA-Z0-9_]*).*/\1/' \
    | sort -u
done < <(find "$DIR" -name '*.vue') > "$tmp"

if sort "$tmp" | uniq -d | grep -q .; then
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    files="$(grep -rlE "(const $name = (async )?\(|function $name\()" --include='*.vue' "$DIR" 2>/dev/null | sed "s#^$DIR/##" | paste -sd', ' -)"
    echo "  $name  ->  $files"
  done < <(sort "$tmp" | uniq -d)
else
  echo "(none found)"
fi
echo
echo "=== scan complete: candidates only, verify each in context ==="
