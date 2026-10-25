#!/bin/sh
# Pre-commit guard (make hooks): refuses a commit that stages
#   - a file over 1 MB, other than the two vendored map libraries;
#   - any data file not listed in PUBLIC_DATA.txt.
# The .gitignore allowlist already keeps data out; this catches a file added by force
# (git add -f) or a pattern widened by mistake. Advan data and anything derived from it
# at fine grain must never be committed (README.md: Data).
set -e
root=$(git rev-parse --show-toplevel)
bad=0
for f in $(git diff --cached --name-only --diff-filter=AM); do
  case "$f" in
    flows/d3.min.js|flows/topojson-client.min.js) continue ;;
  esac
  size=$(wc -c < "$root/$f" | tr -d ' ')
  if [ "$size" -gt 1048576 ]; then
    echo "refused: $f is $size bytes (limit 1 MB)" >&2; bad=1
  fi
  case "$f" in
    *.py|*.sh|*.html|*.md|Makefile|.gitignore|PUBLIC_DATA.txt|requirements.txt|LICENSE) ;;
    *)
      if ! grep -qxF "$f" "$root/PUBLIC_DATA.txt"; then
        echo "refused: $f is not code and is not listed in PUBLIC_DATA.txt" >&2; bad=1
      fi ;;
  esac
done
exit $bad
