#!/usr/bin/env bash
# Install the locally built scaleinn-cli package and verify it.
# Usage: ./scripts/install.sh [path/to/scaleinn-cli_X.Y.Z_amd64.deb]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEB="${1:-}"
if [[ -z "$DEB" ]]; then
    DEB="$(ls -1t "$ROOT"/dist/scaleinn-cli_*.deb 2>/dev/null | head -n1 || true)"
fi
[[ -f "$DEB" ]] || { echo "error: no .deb found. Run ./scripts/build_deb.sh first or pass a path." >&2; exit 1; }

SUDO=""
[[ "$(id -u)" -eq 0 ]] || SUDO="sudo"

echo "Installing $DEB"
# --reinstall: a rebuilt package with the same version number must replace the installed one.
# apt also resolves python3-click / python3-requests.
$SUDO apt-get install -y --reinstall "$(realpath "$DEB")"

echo
command -v scaleinn
scaleinn --version
echo
echo "Next: run 'scaleinn configure'"
