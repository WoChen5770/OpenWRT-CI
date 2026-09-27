#!/bin/bash
# Run from the OpenWrt source root (./wrt). Only selected PassWall targets use official binaries.
set -euo pipefail

case "${WRT_TARGET:-}/${WRT_SUBTARGET:-}/${WRT_CONFIG:-}" in
	x86/64/*)
		ASSET="Xray-linux-64.zip"
		ARCH_DEPENDS="@x86_64"
		ARCH_LABEL="x86-64"
		;;
	mediatek/filogic/TENDA-BE12-PRO-PASSWALL)
		ASSET="Xray-linux-arm64-v8a.zip"
		ARCH_DEPENDS="@aarch64"
		ARCH_LABEL="ARM64"
		;;
	*) exit 0 ;;
esac

TEMPLATE="$GITHUB_WORKSPACE/Scripts/Makefiles/xray-core-prebuilt.mk"
[[ -f "$TEMPLATE" && -d ./feeds/packages && -d ./feeds/luci ]] || {
	echo "Xray: missing template or not running from the OpenWrt source root" >&2
	exit 1
}

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$TMP_DIR/xray-core"
HEADERS=(-H 'Accept: application/vnd.github+json')
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
	HEADERS+=(-H "Authorization: Bearer $GITHUB_TOKEN")
fi

# Query every build, including prereleases. Never fall back to an older release
# when the newest release is still uploading its binary.
for ATTEMPT in 1 2 3; do
	curl --fail --silent --show-error --location --retry 3 \
		--connect-timeout 15 --max-time 120 "${HEADERS[@]}" \
		'https://api.github.com/repos/XTLS/Xray-core/releases?per_page=100' \
		> "$TMP_DIR/releases.json"
	if RELEASE=$(jq -er --arg asset "$ASSET" '
		map(select(.draft != true and .published_at != null))
		| max_by(.published_at)
		| select(.tag_name | strings | length > 0) as $release
		| first(($release.assets // [])[] | select(
			.name == $asset and .state == "uploaded" and (.id | type) == "number"))
		| [$release.tag_name, .id] | @tsv
	' "$TMP_DIR/releases.json"); then
		break
	fi
	if [[ "$ATTEMPT" == 3 ]]; then
		echo "Xray: latest release or its $ASSET is unavailable; refusing an older version" >&2
		exit 1
	fi
	echo "Xray: latest release ZIP is not ready; retrying in 10 seconds ($ATTEMPT/3)" >&2
	sleep 10
done

IFS=$'\t' read -r TAG ASSET_ID <<< "$RELEASE"
VERSION=${TAG#v}
# Keep filenames and Makefile values safe without imposing a three-part version format.
case "$VERSION" in
	''|*[!a-zA-Z0-9._+-]*) echo "Xray: unusable release tag: $TAG" >&2; exit 1 ;;
esac
SOURCE="${ASSET%.zip}-$VERSION-$ASSET_ID.zip"
sed -e "s/@XRAY_VERSION@/$VERSION/g" -e "s/@XRAY_TAG@/$TAG/g" \
	-e "s/@XRAY_SOURCE@/$SOURCE/g" -e "s/@XRAY_ASSET@/$ASSET/g" \
	-e "s/@XRAY_ARCH_DEPENDS@/$ARCH_DEPENDS/g" \
	-e "s/@XRAY_ARCH_LABEL@/$ARCH_LABEL/g" \
	"$TEMPLATE" > "$TMP_DIR/xray-core/Makefile"
if [[ "$WRT_CONFIG" == TENDA-BE12-PRO-PASSWALL ]]; then
	awk '$0 == "@XRAY_COMPRESS@" {
		print "\tupx --best $(PKG_BUILD_DIR)/xray"
		print "\tupx -t $(PKG_BUILD_DIR)/xray"
		next
	} {print}' "$TMP_DIR/xray-core/Makefile" > "$TMP_DIR/Makefile"
	mv "$TMP_DIR/Makefile" "$TMP_DIR/xray-core/Makefile"
else
	sed -i '/@XRAY_COMPRESS@/d' "$TMP_DIR/xray-core/Makefile"
fi

# Remove exact-name recipes and feed symlinks, not xray-plugin or other packages.
find ./package ./feeds/packages/ ./feeds/luci/ -maxdepth 3 \
	\( -type d -o -type l \) -name xray-core -prune -exec rm -rf {} +
mkdir -p ./package
cp -R "$TMP_DIR/xray-core" ./package/xray-core

# Cache only the ZIP, never the release lookup. A re-upload gets a new asset ID.
if [[ -n "${GITHUB_ENV:-}" ]]; then
	printf 'XRAY_SOURCE=%s\n' "$SOURCE" >> "$GITHUB_ENV"
fi
echo "Xray $ARCH_LABEL: using latest official release $TAG (SHA256 check disabled)"
