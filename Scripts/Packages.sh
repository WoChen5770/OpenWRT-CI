#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 VIKINGYFY

#安装和更新软件包
UPDATE_PACKAGE() {
	local PKG_NAME=$1
	local PKG_REPO=$2
	local PKG_BRANCH=$3
	local PKG_SPECIAL=$4
	local PKG_LIST=("$PKG_NAME" $5)  # 第5个参数为自定义名称列表
	local REPO_NAME=${PKG_REPO#*/}
	local REPO_PATH="./package/$REPO_NAME"

	echo " "

	# 删除本地可能存在的不同名称的软件包
	for NAME in "${PKG_LIST[@]}"; do
		# 查找匹配的目录
		echo "Search directory: $NAME"
		local FOUND_DIRS=$(find ./package ./feeds/luci/ ./feeds/packages/ -maxdepth 3 -type d -iname "*$NAME*" 2>/dev/null)

		# 删除找到的目录
		if [ -n "$FOUND_DIRS" ]; then
			while read -r DIR; do
				rm -rf "$DIR"
				echo "Delete directory: $DIR"
			done <<< "$FOUND_DIRS"
		else
			echo "Not fonud directory: $NAME"
		fi
	done

	# 克隆 GitHub 仓库
	git clone --depth=1 --single-branch --branch $PKG_BRANCH "https://github.com/$PKG_REPO.git" $REPO_PATH

	# 处理克隆的仓库
	if [[ "$PKG_SPECIAL" == "pkg" ]]; then
		find $REPO_PATH/*/ -maxdepth 3 -type d -iname "*$PKG_NAME*" -prune -exec cp -rf {} ./package \;
		rm -rf $REPO_PATH
	fi
}

#从大杂烩仓库中提取一组相互依赖的软件包目录
UPDATE_PACKAGE_GROUP() {
	local PKG_REPO=$1
	local PKG_BRANCH=$2
	shift 2
	local PKG_NAMES=("$@")
	local REPO_NAME=${PKG_REPO#*/}
	local REPO_PATH="./package/$REPO_NAME"

	echo " "
	for NAME in "${PKG_NAMES[@]}"; do
		find ./package ./feeds/luci/ ./feeds/packages/ -maxdepth 3 -type d -name "$NAME" \
			-prune -exec rm -rf {} + 2>/dev/null || true
	done

	git clone --depth=1 --single-branch --branch "$PKG_BRANCH" "https://github.com/$PKG_REPO.git" "$REPO_PATH"
	for NAME in "${PKG_NAMES[@]}"; do
		if [ ! -d "$REPO_PATH/$NAME" ]; then
			echo "Package directory not found: $NAME"
			rm -rf "$REPO_PATH"
			return 1
		fi
		cp -rf "$REPO_PATH/$NAME" ./package/
	done
	rm -rf "$REPO_PATH"
}

#提取仓库内的单个软件包；临时克隆避免仓库名与包目录同名时相互覆盖。
UPDATE_NESTED_PACKAGE() (
	local PKG_NAME=$1
	local PKG_REPO=$2
	local PKG_BRANCH=$3
	local PKG_ALIAS=${4:-}
	local TMP_DIR
	TMP_DIR=$(mktemp -d) || exit 1
	trap 'rm -rf "$TMP_DIR"' EXIT

	git clone --depth=1 --single-branch --branch "$PKG_BRANCH" \
		"https://github.com/$PKG_REPO.git" "$TMP_DIR/source" || exit 1
	if [ ! -f "$TMP_DIR/source/$PKG_NAME/Makefile" ]; then
		echo "Package Makefile not found: $PKG_REPO/$PKG_NAME" >&2
		exit 1
	fi

	# 完整获取新源码后，才移除旧目录和 feeds 安装链接，防止重复定义。
	for NAME in "$PKG_NAME" "$PKG_ALIAS"; do
		[ -n "$NAME" ] || continue
		find ./package ./feeds/luci/ ./feeds/packages/ -maxdepth 3 \
			\( -type d -o -type l \) -name "$NAME" -prune -exec rm -rf {} + || exit 1
	done
	cp -R "$TMP_DIR/source/$PKG_NAME" "./package/$PKG_NAME" || exit 1
)

# 调用示例
# UPDATE_PACKAGE "OpenAppFilter" "destan19/OpenAppFilter" "master" "" "custom_name1 custom_name2"
# UPDATE_PACKAGE "open-app-filter" "destan19/OpenAppFilter" "master" "" "luci-app-appfilter oaf" 这样会把原有的open-app-filter，luci-app-appfilter，oaf相关组件删除，不会出现coremark错误。

# UPDATE_PACKAGE "包名" "项目地址" "项目分支" "pkg，可选，从大杂烩中单独提取包名插件"
UPDATE_PACKAGE "argon" "sbwml/luci-theme-argon" "openwrt-25.12"
UPDATE_PACKAGE "aurora" "eamonxg/luci-theme-aurora" "master"
UPDATE_PACKAGE "aurora-config" "eamonxg/luci-app-aurora-config" "master"
UPDATE_PACKAGE "kucat" "sirpdboy/luci-theme-kucat" "master"
UPDATE_PACKAGE "kucat-config" "sirpdboy/luci-app-kucat-config" "master"
UPDATE_PACKAGE "noobwrt" "nooblk-98/luci-theme-noobwrt" "master"
UPDATE_PACKAGE "shadcn" "eamonxg/luci-theme-shadcn" "main"
UPDATE_PACKAGE "theme-fluent" "LazuliKao/luci-theme-fluent" "main"

UPDATE_PACKAGE "momo" "nikkinikki-org/OpenWrt-momo" "main"
UPDATE_PACKAGE "nikki" "nikkinikki-org/OpenWrt-nikki" "main"
UPDATE_PACKAGE "openclash" "vernesong/OpenClash" "dev" "pkg"
UPDATE_PACKAGE "passwall" "Openwrt-Passwall/openwrt-passwall" "main" "pkg"
UPDATE_PACKAGE "passwall2" "Openwrt-Passwall/openwrt-passwall2" "main" "pkg"

# AdGuardHome 面板：替换 Makefile + 应用补丁（/etc/AdGuardHome）+ 开机自启
UPDATE_PACKAGE "luci-app-adguardhome-dashboard" "imonior/luci-app-adguardhome-dashboard" "main"
cp -f "$GITHUB_WORKSPACE/Scripts/Makefiles/luci-app-adguardhome-dashboard.mk" \
	./package/luci-app-adguardhome-dashboard/Makefile
#新安装默认部署到 /etc/AdGuardHome；上游结构变化导致补丁失败时停止构建。
patch --batch --forward -d ./package/luci-app-adguardhome-dashboard -p1 \
	< "$GITHUB_WORKSPACE/Scripts/Patches/adguardhome-etc-directory.patch" || exit 1
# 开机自启迁移及后续面板安装流程使用同一检查脚本。
cp -f "$GITHUB_WORKSPACE/Scripts/Files/adguardhome-dashboard/"* \
	./package/luci-app-adguardhome-dashboard/files/ || exit 1
patch --batch --forward -d ./package/luci-app-adguardhome-dashboard -p1 \
	< "$GITHUB_WORKSPACE/Scripts/Patches/adguardhome-autostart.patch" || exit 1
UPDATE_PACKAGE_GROUP "kenzok8/small" "master" "dae" "daed" "luci-app-daede" "v2ray-geodata"
UPDATE_PACKAGE "diskman" "sbwml/luci-app-diskman" "main"
# 不集成到固件：磁盘/分区管理类（mini-diskmanager）
# UPDATE_PACKAGE "diskmanager" "4IceG/luci-app-mini-diskmanager" "main"
UPDATE_PACKAGE "easytier" "EasyTier/luci-app-easytier" "main"
# 完全禁用 QModem，保留拉取代码供以后按需恢复。
# UPDATE_PACKAGE "qmodem" "FUjr/QModem" "main"
UPDATE_PACKAGE "viking" "VIKINGYFY/packages" "main" "" "axonhub gecoosac sing-box luci-app-homeproxy luci-app-timewol luci-app-wolplus luci-app-wolultra"
#Bandix 前后端均采用上游 main 分支的包定义，保留下载哈希校验。
UPDATE_NESTED_PACKAGE "openwrt-bandix" "timsaya/openwrt-bandix" "main" "bandix" || exit 1
UPDATE_NESTED_PACKAGE "luci-app-bandix" "timsaya/luci-app-bandix" "main" || exit 1
UPDATE_PACKAGE "vnt" "lmq8267/luci-app-vnt" "main"

UPDATE_PACKAGE "ddns-go" "sirpdboy/luci-app-ddns-go" "main"
UPDATE_PACKAGE "mosdns" "sbwml/luci-app-mosdns" "v5" "" "v2dat"
UPDATE_PACKAGE "netspeedtest" "sirpdboy/netspeedtest" "main" "" "homebox ookla-speedtest"
UPDATE_PACKAGE "netwizard" "sirpdboy/luci-app-netwizard" "main"
UPDATE_PACKAGE "openlist2" "sbwml/luci-app-openlist2" "main"
# 不集成到固件：磁盘/分区管理类（partexp）
# UPDATE_PACKAGE "partexp" "sirpdboy/luci-app-partexp" "main"
UPDATE_PACKAGE "qbittorrent" "sbwml/luci-app-qbittorrent" "master" "" "qt6base qt6tools rblibtorrent"
UPDATE_PACKAGE "quickfile" "sbwml/luci-app-quickfile" "main"
UPDATE_PACKAGE "timecontrol" "sirpdboy/luci-app-timecontrol" "main"

UPDATE_PACKAGE "natmapt" "muink/openwrt-natmapt" "master"
UPDATE_PACKAGE "stuntman" "muink/openwrt-stuntman" "master"
UPDATE_PACKAGE "luci-app-natmapt" "muink/luci-app-natmapt" "master"

UPDATE_PACKAGE "airpi3000m" "LianXia233/luci-app-airpi3000m-fancontrol" "main"
UPDATE_PACKAGE "chfs" "LianXia233/luci-app-chfs" "main"
# 不集成到固件：5G/移动网络模组类（fm350）
# UPDATE_PACKAGE "fm350" "LianXia233/luci-app-fm350" "main"
UPDATE_PACKAGE "h5000m" "LianXia233/luci-app-h5000m-netmode" "main"
# 不集成到固件：5G/移动网络模组类（mt5700）
# UPDATE_PACKAGE "mt5700" "LianXia233/luci-app-mt5700" "main"
# 不集成到固件：5G/移动网络模组类（mt5700m）
# UPDATE_PACKAGE "mt5700m" "LianXia233/luci-app-mt5700m" "main"
UPDATE_PACKAGE "netmonitor" "LianXia233/luci-app-netmonitor" "main"
# UPDATE_PACKAGE "qmodem-generic" "LianXia233/luci-app-qmodem-generic" "main"

# 完全移除源码或 feeds 残留的 QModem 包及安装链接。
# 必须在所有软件源更新后、生成包元数据前执行；仅设为 n 无法消除 Kconfig 环。
for PACKAGE_ROOT in ./package ./feeds; do
	[ -d "$PACKAGE_ROOT" ] || continue
	find "$PACKAGE_ROOT" \( -type d -o -type l \) \( \
		-iname 'qmodem*' -o -iname 'luci-app-qmodem*' -o \
		-iname 'luci-i18n-qmodem*' \) -prune \
		-exec rm -rf -- {} + || exit 1
done

#最后替换 x86-64 的 Xray 定义，避免其他软件源覆盖；其他架构保持原样。
bash "$GITHUB_WORKSPACE/Scripts/Xray.sh" || exit 1
# AdGuard Home definition is generated after private/manual config overrides.

#更新软件包版本
UPDATE_VERSION() {
	local PKG_NAME=$1
	local PKG_MARK=${2:-false}
	local PKG_FILES=$(find ./ ./feeds/packages/ -maxdepth 3 -type f -wholename "*/$PKG_NAME/Makefile")

	if [ -z "$PKG_FILES" ]; then
		echo "$PKG_NAME not found!"
		return
	fi

	echo -e "\n$PKG_NAME version update has started!"

	for PKG_FILE in $PKG_FILES; do
		local PKG_REPO=$(grep -Po "PKG_SOURCE_URL:=https://.*github.com/\K[^/]+/[^/]+(?=.*)" $PKG_FILE)
		local PKG_TAG=$(curl -sL "https://api.github.com/repos/$PKG_REPO/releases" | jq -r "map(select(.prerelease == $PKG_MARK)) | first | .tag_name")

		local OLD_VER=$(grep -Po "PKG_VERSION:=\K.*" "$PKG_FILE")
		local OLD_URL=$(grep -Po "PKG_SOURCE_URL:=\K.*" "$PKG_FILE")
		local OLD_FILE=$(grep -Po "PKG_SOURCE:=\K.*" "$PKG_FILE")
		local OLD_HASH=$(grep -Po "PKG_HASH:=\K.*" "$PKG_FILE")

		local PKG_URL=$([[ "$OLD_URL" == *"releases"* ]] && echo "${OLD_URL%/}/$OLD_FILE" || echo "${OLD_URL%/}")

		local NEW_VER=$(echo $PKG_TAG | sed -E 's/[^0-9]+/\./g; s/^\.|\.$//g')
		local NEW_URL=$(echo $PKG_URL | sed "s/\$(PKG_VERSION)/$NEW_VER/g; s/\$(PKG_NAME)/$PKG_NAME/g")
		local NEW_HASH=$(curl -sL "$NEW_URL" | sha256sum | cut -d ' ' -f 1)

		echo "old version: $OLD_VER $OLD_HASH"
		echo "new version: $NEW_VER $NEW_HASH"

		if [[ "$NEW_VER" =~ ^[0-9].* ]] && dpkg --compare-versions "$OLD_VER" lt "$NEW_VER"; then
			sed -i "s/PKG_VERSION:=.*/PKG_VERSION:=$NEW_VER/g" "$PKG_FILE"
			sed -i "s/PKG_HASH:=.*/PKG_HASH:=$NEW_HASH/g" "$PKG_FILE"
			echo "$PKG_FILE version has been updated!"
		else
			echo "$PKG_FILE version is already the latest!"
		fi
	done
}

#UPDATE_VERSION "软件包名" "测试版，true，可选，默认为否"
#UPDATE_VERSION "sing-box"

#引入私有扩展脚本
if [ -f "$GITHUB_WORKSPACE/Scripts/PRIVATE.sh" ]; then
	source "$GITHUB_WORKSPACE/Scripts/PRIVATE.sh"
fi

# BE12 Pro: small prebuilt ARM64 UPX and a manual, checked /tmp-first core updater.
mkdir -p ./package/upx-arm64-static ./package/owrt-core-update/files
cp -f "$GITHUB_WORKSPACE/Scripts/Makefiles/upx-arm64-static.mk" \
    ./package/upx-arm64-static/Makefile || exit 1
cp -f "$GITHUB_WORKSPACE/Scripts/Makefiles/owrt-core-update.mk" \
    ./package/owrt-core-update/Makefile || exit 1
cp -f "$GITHUB_WORKSPACE/Scripts/Files/core-update/owrt-core-update" \
    ./package/owrt-core-update/files/owrt-core-update || exit 1
