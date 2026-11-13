#!/usr/bin/env bash
# Remove the scaleinn-cli package.
# Your per-user data in ~/.scaleinn (config.json, credentials.json, logs) is
# deliberately NOT touched, not even by --purge. Delete it yourself if desired:
#     rm -rf ~/.scaleinn
set -euo pipefail

SUDO=""
[[ "$(id -u)" -eq 0 ]] || SUDO="sudo"

$SUDO apt-get remove -y scaleinn-cli
echo "scaleinn-cli removed. Your ~/.scaleinn directory was left in place."
