#!/usr/bin/env bash
# Install an isolated, NON-RUNNING HA test scaffold on the target Docker server.
# Run from the repository root as a user with sudo privileges.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="${1:-/srv/containers/ha-opcua-test}"

if [ -e "$target" ]; then
  echo "ABORT: Test directory already exists: $target" >&2
  echo "No files were changed." >&2
  exit 1
fi
if [ "$target" = "/srv/containers/homeassistant" ] || [ "$target" = "/srv/containers/homeassistant/config" ]; then
  echo "ABORT: Refusing to use production Home Assistant path" >&2
  exit 1
fi
if [ ! -f "$repo_root/custom_components/asyncua/manifest.json" ]; then
  echo "ABORT: Run this script from the integration repository root." >&2
  exit 1
fi

sudo install -d "$target/config/custom_components"
sudo cp -a "$repo_root/custom_components/asyncua" "$target/config/custom_components/asyncua"
sudo cp "$repo_root/docs/compose.test.example.yaml" "$target/compose.yaml"
sudo cp "$repo_root/docs/configuration.test.example.yaml" "$target/config/configuration.yaml"

echo "Isolated test scaffold prepared: $target"
echo "No containers were started. Production HA was not changed."
echo "NEXT: Edit $target/config/configuration.yaml with one SAFE read-only PLC node."
echo "THEN: cd $target && docker compose -f compose.yaml up -d"
