#!/bin/bash
# Build-host UPX, separate from the ARM64 executable bundled into the firmware.
set -euo pipefail
TAG=v5.2.1
ASSET=upx-5.2.1-amd64_linux.tar.xz
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
curl -fsSL --retry 3 https://api.github.com/repos/upx/upx/releases/tags/$TAG > "$TMP/release.json"
HASH=$(jq -er --arg name "$ASSET" 'first(.assets[] | select(.name == $name and .state == "uploaded") | .digest | select(startswith("sha256:")) | sub("^sha256:"; ""))' "$TMP/release.json")
[[ "$HASH" =~ ^[0-9a-f]{64}$ ]] || exit 1
curl -fsSL --retry 3 "https://github.com/upx/upx/releases/download/$TAG/$ASSET" -o "$TMP/$ASSET"
echo "$HASH  $TMP/$ASSET" | sha256sum -c -
tar -xJf "$TMP/$ASSET" -C "$TMP"
sudo install -m 755 "$TMP/upx-5.2.1-amd64_linux/upx" /usr/local/bin/upx
upx --version | head -1
