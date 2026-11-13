#!/usr/bin/env bash
# Build scaleinn-cli_<version>_amd64.deb into ./dist
#
# Usage:  ./scripts/build_deb.sh
#         SKIP_TESTS=1 ./scripts/build_deb.sh     # skip the pytest run during the build
#
# Build requirements (Ubuntu/Debian):
#   sudo apt install build-essential debhelper dh-python pybuild-plugin-pyproject \
#        python3-all python3-setuptools python3-click python3-requests python3-pytest
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

die() { echo "error: $*" >&2; exit 1; }

# --- version must agree between the code and debian/changelog -----------------
VERSION="$(sed -nE 's/^__version__ *= *"([^"]+)".*/\1/p' src/scaleinn/version.py)"
CHANGELOG_VERSION="$(head -n1 packaging/debian/changelog | sed -E 's/^[^(]+\(([^)]+)\).*/\1/')"
[[ -n "$VERSION" ]] || die "could not read version from src/scaleinn/version.py"
[[ "$VERSION" == "$CHANGELOG_VERSION" ]] || \
    die "version mismatch: version.py=$VERSION, packaging/debian/changelog=$CHANGELOG_VERSION"

command -v dpkg-buildpackage >/dev/null || die "dpkg-buildpackage not found (apt install build-essential)"

# --- stage a clean source tree ------------------------------------------------
BUILD_DIR="$ROOT/.scaleinn-build"
SRC_DIR="$BUILD_DIR/scaleinn-cli-$VERSION"
rm -rf "$BUILD_DIR"
mkdir -p "$SRC_DIR"

cp -r src tests pyproject.toml requirements.txt README.md LICENSE "$SRC_DIR/"
cp -r packaging/debian "$SRC_DIR/debian"
chmod +x "$SRC_DIR/debian/rules"
find "$SRC_DIR" \( -name __pycache__ -o -name '*.egg-info' -o -name .pytest_cache \) -prune -exec rm -rf {} +

# --- build ---------------------------------------------------------------------
cd "$SRC_DIR"
if ! dpkg-checkbuilddeps 2>/dev/null; then
    dpkg-checkbuilddeps || true
    die "missing build dependencies (see the list above)"
fi
if [[ "${SKIP_TESTS:-0}" == "1" ]]; then
    export DEB_BUILD_OPTIONS="${DEB_BUILD_OPTIONS:-} nocheck"
fi
dpkg-buildpackage -us -uc -b

# --- collect -------------------------------------------------------------------
mkdir -p "$ROOT/dist"
cp "$BUILD_DIR"/scaleinn-cli_"${VERSION}"_*.deb "$ROOT/dist/"
echo
echo "Built:"
ls -1 "$ROOT"/dist/scaleinn-cli_"${VERSION}"_*.deb
echo
echo "Install with:  sudo apt install ./dist/scaleinn-cli_${VERSION}_amd64.deb"
