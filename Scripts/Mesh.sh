#!/bin/bash
# S20P / BE12 Pro / BE6500: fetch xxosdev/luci-app-mesh without changing its runtime defaults.
set -euo pipefail

case "${WRT_CONFIG:-}" in
	SUPERGATEWAY-S20P|TENDA-BE12-PRO|XIAOMI-BE6500) ;;
	*) exit 0 ;;
esac

: "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE must point to the CI repository}"
for MESH_ROOT in ./package ./feeds/luci ./feeds/packages; do
	if [ ! -d "$MESH_ROOT" ]; then
		echo "Mesh integration must run in the prepared OpenWrt tree: missing $MESH_ROOT" >&2
		exit 1
	fi
done

MESH_TMP=$(mktemp -d)
trap 'rm -rf -- "$MESH_TMP"' EXIT

git clone --depth=1 --single-branch --branch main \
	https://github.com/xxosdev/luci-app-mesh.git "$MESH_TMP/source"
test -f "$MESH_TMP/source/Makefile"
test -f "$MESH_TMP/source/root/etc/config/mesh"

# Filogic and qualcommbe default to full wpad-openssl, which includes 802.11s/SAE.
# Do not install the conflicting wpad-mesh-openssl variant alongside it.
patch --batch --forward --fuzz=0 -d "$MESH_TMP/source" -p1 \
	< "$GITHUB_WORKSPACE/Scripts/Patches/mesh-wpad-openssl.patch"

# Fetch and validate first; remove only exact-name packages and feeds links.
find ./package ./feeds/luci ./feeds/packages -maxdepth 3 \
	\( -type d -o -type l \) -name luci-app-mesh -prune -exec rm -rf -- {} +
cp -R "$MESH_TMP/source" ./package/luci-app-mesh
echo "Mesh source: $(git -C "$MESH_TMP/source" rev-parse HEAD)"
