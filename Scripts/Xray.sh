#!/bin/bash
# Run from the OpenWrt package directory. Other targets keep their original recipe.
set -euo pipefail

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
	if RELEASE=$(jq -er '
		map(select(.draft != true and .published_at != null))
		| max_by(.published_at)
		| select(.tag_name | strings | length > 0) as $release
		| first(($release.assets // [])[] | select(
			.name == "Xray-linux-64.zip" and .state == "uploaded" and (.id | type) == "number"))
		| [$release.tag_name, .id] | @tsv
	' "$TMP_DIR/releases.json"); then
		break
	fi
	if [[ "$ATTEMPT" == 3 ]]; then
		echo "Xray: latest release or its x86-64 ZIP is unavailable; refusing an older version" >&2
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
SOURCE="Xray-linux-64-$VERSION-$ASSET_ID.zip"
sed -e "s/@XRAY_VERSION@/$VERSION/g" -e "s/@XRAY_TAG@/$TAG/g" \
	-e "s/@XRAY_ASSET_ID@/$ASSET_ID/g" "$TEMPLATE" > "$TMP_DIR/xray-core/Makefile"

# Remove exact-name recipes and feed symlinks, not xray-plugin or other packages.
find ./ ../feeds/packages/ ../feeds/luci/ -maxdepth 3 \
	\( -type d -o -type l \) -name xray-core -prune -exec rm -rf {} +
cp -R "$TMP_DIR/xray-core" ./xray-core

# Cache only the ZIP, never the release lookup. A re-upload gets a new asset ID.
if [[ -n "${GITHUB_ENV:-}" ]]; then
	printf 'XRAY_SOURCE=%s\n' "$SOURCE" >> "$GITHUB_ENV"
fi
echo "Xray x86-64: using latest official release $TAG (SHA256 check disabled)"
