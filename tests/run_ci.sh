#!/usr/bin/env bash
# Local parity with .github/workflows/ci.yml
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== packaging =="
test -f LICENSE
test -f SECURITY.md
test -f README.md
test -f .gitignore
test -f docs/pre-publish.md
test -f .github/workflows/ci.yml
test -x tests/run_ci.sh
echo "OK: packaging layout"

echo "== unittest =="
python3 -m unittest discover -s tests -v

echo "== publish hygiene =="
if grep -RIn --exclude-dir=.git --exclude-dir=__pycache__ \
  -e 'BEGIN OPENSSH PRIVATE' -e 'BEGIN RSA PRIVATE' -e 'mxhash' \
  -- proxmoxlib roles README.md; then
  echo "secret or org fingerprint in product sources" >&2
  exit 1
fi

echo "CI checks passed."
