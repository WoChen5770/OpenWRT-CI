# OpenWRT-CI

基于 [ImmortalWrt](https://github.com/VIKINGYFY/immortalwrt) 的自用固件编译配置。默认管理地址：`192.168.123.1`。

## 编译

每日 `Auto-Clean` 完成后自动编译 X86、Super Gateway S20P 和 Tenda BE12 Pro；也可在 Actions 中手动运行相应工作流。BE12 Pro 手动运行时可选择 `BOTH`、`PASSWALL` 或 `DAED`。

| 固件 | 默认内容 |
| --- | --- |
| X86 | 虚拟机适配；PassWall + Xray、EasyTier、AdGuard Home 核心及面板，不集成 WiFi 驱动 |
| S20P | 2GB 内存 + 128GB 存储；PassWall + Xray、daed、Bandix、EasyTier、AdGuard Home 核心及面板，保留上游 WiFi 和存储驱动 |
| BE12 Pro PassWall 版 | PassWall + Xray，不集成 daed |
| BE12 Pro daed 版 | daed，不集成 PassWall + Xray |

X86 和 S20P 使用软件源自带的 `adguardhome` 包，沿用默认二进制 `/usr/bin/AdGuardHome`、配置 `/etc/adguardhome/adguardhome.yaml` 和服务 `/etc/init.d/adguardhome`。首次开机启用服务，不改动 DNS、监听端口或部署路径。

BE12 Pro 两版均不集成 AdGuard Home 面板或核心，也不再执行相关补丁、ARM64 核心预置及数据转存 `/tmp` 的逻辑。Bandix、EasyTier 默认不集成，仍可通过 `Config/PRIVATE.txt` 或工作流的 `PACKAGE` 输入自行选用。

## S20P

- Actions 工作流：`SUPERGATEWAY-S20P`，配置文件：`Config/SUPERGATEWAY-S20P.txt`，设备标识：`supergateway_s20p`。
- 使用上游 MT7986A / Filogic 设备定义，保留 2GB 内存设置、WiFi、USB、MMC/NVMe 及文件系统支持；不修改 eMMC 分区布局，也不自动扩容到 128GB。
- Xray 使用最新官方 ARM64 二进制（包含预发布版本），不做 UPX 压缩；不预置 BE12 Pro 的手动核心更新器，也不把 AdGuard Home 数据转存到 `/tmp`。
- 保留 EasyTier 核心与 LuCI，不额外集成 Web Console。管理地址仍为 `192.168.123.1`。

## BE12 Pro 可选功能

- PassWall 版预置手动核心更新命令 `owrt-core-update xray`。更新核心前请备份配置并确认剩余空间。
- daed 版默认不带更新器；如需使用，同时选用 `CONFIG_PACKAGE_owrt-core-update=y` 和 `CONFIG_PACKAGE_upx-arm64-static=y`。
