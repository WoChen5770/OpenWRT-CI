# OpenWRT-CI

基于 [ImmortalWrt](https://github.com/VIKINGYFY/immortalwrt) 的自用固件编译配置。默认管理地址：`192.168.123.1`。

## 编译

每日 `Auto-Clean` 完成后自动编译 X86 和 Tenda BE12 Pro；也可在 Actions 中手动运行相应工作流。BE12 Pro 手动运行时可选择 `BOTH`、`PASSWALL` 或 `DAED`。

| 固件 | 默认内容 |
| --- | --- |
| X86 | 虚拟机适配；PassWall + Xray、EasyTier 等，不集成 WiFi 驱动 |
| BE12 Pro PassWall 版 | PassWall + Xray，不集成 daed |
| BE12 Pro daed 版 | daed，不集成 PassWall + Xray |

BE12 Pro 两版默认都不集成 Bandix、EasyTier 和 AdGuard Home；可通过 `Config/PRIVATE.txt` 或工作流的 `PACKAGE` 输入自行选用。

## BE12 Pro 可选功能

- 预置 AdGuard Home：同时选用 `CONFIG_PACKAGE_luci-app-adguardhome-dashboard=y` 和 `CONFIG_PACKAGE_adguardhome-core-prebuilt=y`。选用后工作数据放在 `/tmp`，**重启会清空日志、统计和下载的过滤数据**。
- PassWall 版预置手动核心更新命令 `owrt-core-update xray`；如额外预置 AdGuard Home，可运行 `owrt-core-update adguardhome`。更新核心前请备份配置并确认剩余空间。
- daed 版默认不带更新器；如需使用，同时选用 `CONFIG_PACKAGE_owrt-core-update=y` 和 `CONFIG_PACKAGE_upx-arm64-static=y`。

