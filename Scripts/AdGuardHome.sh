#!/bin/bash
# Resolve the latest stable official ARM64 release for both BE12 Pro images.
set -euo pipefail
[[ "${WRT_CONFIG:-}" == TENDA-BE12-PRO-* ]] || exit 0

TEMPLATE="$GITHUB_WORKSPACE/Scripts/Makefiles/adguardhome-core-prebuilt.mk"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
HEADERS=(-H 'Accept: application/vnd.github+json')
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
	HEADERS+=(-H "Authorization: Bearer $GITHUB_TOKEN")
fi
curl -fsSL --retry 3 "${HEADERS[@]}" \
	https://api.github.com/repos/AdguardTeam/AdGuardHome/releases/latest > "$TMP/release.json"
IFS=$'\t' read -r TAG ASSET_ID HASH < <(jq -er '
  select(.draft == false and .prerelease == false) as $release
  | first($release.assets[] | select(.name == "AdGuardHome_linux_arm64.tar.gz" and .state == "uploaded" and (.digest | startswith("sha256:"))))
  | [$release.tag_name, (.id | tostring), (.digest | sub("^sha256:"; ""))] | @tsv
' "$TMP/release.json")
[[ "$TAG" =~ ^v[0-9][a-zA-Z0-9._+-]*$ && "$HASH" =~ ^[0-9a-f]{64}$ ]] || {
	echo 'AdGuard Home: invalid release metadata' >&2; exit 1;
}
VERSION=${TAG#v}
SOURCE="AdGuardHome_linux_arm64-$VERSION-$ASSET_ID.tar.gz"
mkdir -p ./package/adguardhome-core-prebuilt
sed -e "s/@AGH_VERSION@/$VERSION/g" -e "s/@AGH_TAG@/$TAG/g" \
	-e "s/@AGH_SOURCE@/$SOURCE/g" -e "s/@AGH_HASH@/$HASH/g" \
	"$TEMPLATE" > ./package/adguardhome-core-prebuilt/Makefile
echo "AdGuard Home ARM64: $TAG ($SOURCE), UPX at build time"
