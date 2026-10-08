# OpenWRT-CI

基于 [ImmortalWrt](https://github.com/VIKINGYFY/immortalwrt) 的自用固件编译配置。默认管理地址：`192.168.123.1`。

## 编译

每日 `Auto-Clean` 完成后自动编译 X86 和 Tenda BE12 Pro；也可在 Actions 中手动运行相应工作流。BE12 Pro 手动运行时可选择 `BOTH`、`PASSWALL` 或 `DAED`。

| 固件 | 默认内容 |
| --- | --- |
| X86 | 虚拟机适配；PassWall + Xray、EasyTier、AdGuard Home 核心及面板，不集成 WiFi 驱动 |
| BE12 Pro PassWall 版 | PassWall + Xray，不集成 daed |
| BE12 Pro daed 版 | daed，不集成 PassWall + Xray |

X86 使用软件源自带的 `adguardhome` 包，沿用默认二进制 `/usr/bin/AdGuardHome`、配置 `/etc/adguardhome/adguardhome.yaml` 和服务 `/etc/init.d/adguardhome`。首次开机启用服务，不改动 DNS、监听端口或部署路径。

BE12 Pro 两版均不集成 AdGuard Home 面板或核心，也不再执行相关补丁、ARM64 核心预置及数据转存 `/tmp` 的逻辑。Bandix、EasyTier 默认不集成，仍可通过 `Config/PRIVATE.txt` 或工作流的 `PACKAGE` 输入自行选用。

## BE12 Pro 可选功能

- PassWall 版预置手动核心更新命令 `owrt-core-update xray`。更新核心前请备份配置并确认剩余空间。
- daed 版默认不带更新器；如需使用，同时选用 `CONFIG_PACKAGE_owrt-core-update=y` 和 `CONFIG_PACKAGE_upx-arm64-static=y`。
