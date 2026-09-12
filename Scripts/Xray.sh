#!/bin/bash
# Run from the OpenWrt package directory. Other targets keep their original recipe.
set -eu

if [[ "${WRT_TARGET:-}" != "x86" || "${WRT_SUBTARGET:-}" != "64" ]]; then
	exit 0
fi

TEMPLATE="$GITHUB_WORKSPACE/Scripts/Makefiles/xray-core-prebuilt.mk"
[[ -f "$TEMPLATE" && -d ../feeds/packages && -d ../feeds/luci ]] || {
	echo "Xray: missing template or not running from the OpenWrt package directory" >&2
	exit 1
}

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$TMP_DIR/xray-core"
# Query on every invocation, independently of the restored build cache.
# Resolve once per build so version, URL and SHA256 cannot drift during compilation.
curl --fail --silent --show-error --location --retry 3 \
	--connect-timeout 15 --max-time 120 \
	-H 'Accept: application/vnd.github+json' \
	'https://api.github.com/repos/XTLS/Xray-core/releases?per_page=100' \
	> "$TMP_DIR/releases.json"
python3 "$GITHUB_WORKSPACE/Scripts/resolve_xray.py" \
	"$TMP_DIR/releases.json" "$TEMPLATE" "$TMP_DIR/xray-core/Makefile"

# Remove exact-name recipes and feed symlinks, not xray-plugin or other packages.
find ./ ../feeds/packages/ ../feeds/luci/ -maxdepth 3 \
	\( -type d -o -type l \) -name xray-core -prune -exec rm -rf {} +
cp -R "$TMP_DIR/xray-core" ./xray-core

echo "Xray x86-64: using dynamically resolved official release with verified SHA256 metadata"
grep -E '^PKG_VERSION:=|^PKG_HASH:=' ./xray-core/Makefile
