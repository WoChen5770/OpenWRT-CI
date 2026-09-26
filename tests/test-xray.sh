#!/bin/bash
# Offline smoke test for selecting the official Xray binary per target.
set -euo pipefail

WORKSPACE=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/wrt/package" "$TMP/wrt/feeds/packages" "$TMP/wrt/feeds/luci"
cat > "$TMP/releases.json" <<'JSON'
[
  {"tag_name":"v1.2.3","published_at":"2026-09-26T12:00:00Z","draft":false,"assets":[
    {"name":"Xray-linux-64.zip","state":"uploaded","id":101},
    {"name":"Xray-linux-arm64-v8a.zip","state":"uploaded","id":102}
  ]},
  {"tag_name":"v1.2.2","published_at":"2026-09-25T12:00:00Z","draft":false,"assets":[
    {"name":"Xray-linux-64.zip","state":"uploaded","id":99},
    {"name":"Xray-linux-arm64-v8a.zip","state":"uploaded","id":100}
  ]}
]
JSON
cat > "$TMP/bin/curl" <<'SH'
#!/bin/sh
cat "$XRAY_TEST_RELEASES"
SH
chmod +x "$TMP/bin/curl"
export GITHUB_WORKSPACE="$WORKSPACE" XRAY_TEST_RELEASES="$TMP/releases.json"
export PATH="$TMP/bin:$PATH" GITHUB_ENV="$TMP/github-env"
cd "$TMP/wrt"

WRT_TARGET=x86 WRT_SUBTARGET=64 WRT_CONFIG=X86 bash "$WORKSPACE/Scripts/Xray.sh"
grep -qx 'PKG_SOURCE:=Xray-linux-64-1.2.3-101.zip' package/xray-core/Makefile
grep -qx 'PKG_SOURCE_URL_FILE:=Xray-linux-64.zip' package/xray-core/Makefile
grep -qx '  DEPENDS:=@x86_64 +ca-bundle' package/xray-core/Makefile

grep -qx 'XRAY_SOURCE=Xray-linux-64-1.2.3-101.zip' "$GITHUB_ENV"
: > "$GITHUB_ENV"
WRT_TARGET=mediatek WRT_SUBTARGET=filogic WRT_CONFIG=TENDA-BE12-PRO-PASSWALL bash "$WORKSPACE/Scripts/Xray.sh"
grep -qx 'PKG_SOURCE:=Xray-linux-arm64-v8a-1.2.3-102.zip' package/xray-core/Makefile
grep -qx 'PKG_SOURCE_URL_FILE:=Xray-linux-arm64-v8a.zip' package/xray-core/Makefile
grep -qx '  DEPENDS:=@aarch64 +ca-bundle' package/xray-core/Makefile
grep -qx 'XRAY_SOURCE=Xray-linux-arm64-v8a-1.2.3-102.zip' "$GITHUB_ENV"

: > "$GITHUB_ENV"
WRT_TARGET=mediatek WRT_SUBTARGET=filogic WRT_CONFIG=TENDA-BE12-PRO-DAED bash "$WORKSPACE/Scripts/Xray.sh"
[[ ! -s "$GITHUB_ENV" ]]
# A newer release without the target asset must fail, not silently use an older release.
cat > "$TMP/missing-arm64.json" <<'JSON'
[
  {"tag_name":"v1.2.4","published_at":"2026-09-27T12:00:00Z","draft":false,"assets":[
    {"name":"Xray-linux-64.zip","state":"uploaded","id":103}
  ]},
  {"tag_name":"v1.2.3","published_at":"2026-09-26T12:00:00Z","draft":false,"assets":[
    {"name":"Xray-linux-arm64-v8a.zip","state":"uploaded","id":102}
  ]}
]
JSON
cat > "$TMP/bin/sleep" <<'SH'
#!/bin/sh
exit 0
SH
chmod +x "$TMP/bin/sleep"
export XRAY_TEST_RELEASES="$TMP/missing-arm64.json"
if WRT_TARGET=mediatek WRT_SUBTARGET=filogic WRT_CONFIG=TENDA-BE12-PRO-PASSWALL \
  bash "$WORKSPACE/Scripts/Xray.sh" > "$TMP/failed.log" 2>&1; then
  echo 'Xray accepted an older ARM64 release' >&2
  exit 1
fi
grep -q 'refusing an older version' "$TMP/failed.log"
echo 'Xray target selection and latest-only guard: OK'
