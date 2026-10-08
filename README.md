# OpenWRT-CI

基于 [ImmortalWrt](https://github.com/VIKINGYFY/immortalwrt) 的自用固件编译配置。默认管理地址：`192.168.123.1`。

## Web 管理访问

默认同时提供 HTTP（80）和 HTTPS（443），HTTP 不再自动跳转到 HTTPS。首次开机脚本仅保留 HTTPS 监听，不改写 `uhttpd.main.redirect_https`：全新配置沿用[上游默认值](https://github.com/VIKINGYFY/immortalwrt/blob/owrt/package/network/services/uhttpd/files/uhttpd.config) `0`，也不覆盖用户手动设置。

如需强制跳转，可通过 SSH 登录路由器后手动执行：

```sh
uci set uhttpd.main.redirect_https='1'
uci commit uhttpd
/etc/init.d/uhttpd restart
```

关闭时将上面的 `1` 改为 `0` 后执行同样命令。保留配置升级不会自动清除旧固件留下的 `redirect_https=1`；如果升级后仍会跳转，也需手动关闭。

## 编译

每日 `Auto-Clean` 完成后自动编译 X86、Super Gateway S20P 和 Tenda BE12 Pro；也可在 Actions 中手动运行相应工作流。BE12 Pro 手动运行时可选择 `BOTH`、`PASSWALL` 或 `DAED`。

| 固件 | 默认内容 |
| --- | --- |
| X86 | 虚拟机适配；PassWall + Xray、EasyTier、AdGuard Home 核心及面板，不集成 WiFi 驱动 |
| S20P | 2GB 内存 + 128GB 存储；PassWall + Xray、daed、Bandix、EasyTier、AdGuard Home 核心及面板、Mesh 组网，保留上游 WiFi 和存储驱动 |
| BE12 Pro PassWall 版 | PassWall + Xray、Mesh 组网，不集成 daed |
| BE12 Pro daed 版 | daed、Mesh 组网，不集成 PassWall + Xray |

X86 和 S20P 的核心 `adguardhome` 与面板 [`luci-app-adguardhome`](https://github.com/immortalwrt/luci/tree/master/applications/luci-app-adguardhome) 均使用 ImmortalWrt 软件源的原生软件包，不再拉取 `luci-app-adguardhome-dashboard`，也不应用自定义面板 Makefile、补丁或自启脚本。沿用默认二进制 `/usr/bin/AdGuardHome`、配置 `/etc/adguardhome/adguardhome.yaml` 和服务 `/etc/init.d/adguardhome`，不改动 DNS、监听端口或部署路径。

全新配置沿用上游默认的未启用状态，需在 LuCI 的 AdGuard Home 页面勾选“启用”并“保存并应用”；不再强制修改已有配置的启用状态。LuCI 面板管理服务及运行参数，过滤规则、查询日志等仍通过 AdGuard Home 核心自带的 Web 界面配置，不再提供 Dashboard 的在线升级和备份管理入口。

BE12 Pro 两版均不集成 AdGuard Home 面板或核心，也不再执行相关补丁、ARM64 核心预置及数据转存 `/tmp` 的逻辑。Bandix、EasyTier 默认不集成，仍可通过 `Config/PRIVATE.txt` 或工作流的 `PACKAGE` 输入自行选用。

## S20P

- Actions 工作流：`SUPERGATEWAY-S20P`，配置文件：`Config/SUPERGATEWAY-S20P.txt`，设备标识：`supergateway_s20p`。
- 使用上游 MT7986A / Filogic 设备定义，保留 2GB 内存设置、WiFi、USB、MMC/NVMe 及文件系统支持；不修改 eMMC 分区布局，也不自动扩容到 128GB。
- Xray 使用最新官方 ARM64 二进制（包含预发布版本），不做 UPX 压缩；不预置 BE12 Pro 的手动核心更新器，也不把 AdGuard Home 数据转存到 `/tmp`。
- 保留 EasyTier 核心与 LuCI，不额外集成 Web Console。管理地址仍为 `192.168.123.1`。

## Mesh 组网（S20P / BE12 Pro）

S20P 和 BE12 Pro 两版默认集成 [dffxy/luci-app-mesh](https://gitee.com/dffxy/luci-app-mesh) 的 `master` 分支，配套 802.11s、batman-adv、`batctl-default`、LuCI batman-adv 协议支持及 DAWN/umdns。X86 不集成。构建时仅把插件的 `wpad-mesh-openssl` 依赖改为 Filogic 默认的完整 `wpad-openssl`（已包含 Mesh/SAE），避免两个互斥版本同时安装；界面、服务脚本和默认配置不修改。

保留上游 `enabled=0`：仅预装，不自动组网。刷入后在“网络 → Mesh 组网”检查无线能力并配置角色、Mesh ID 和密码。启用子节点会由插件合并 WAN/LAN、关闭本机 DHCP，并改为从主节点获取管理地址；操作前请备份配置并留意回滚确认提示。

已知兼容限制：上游 `meshctl` 的配置同步请求固定使用 HTTP，且 `curl` 未开启跟随跳转。本仓库默认不强制跳转；若手动开启 HTTP → HTTPS 跳转或关闭 HTTP 监听，子节点自动同步可能失败。Mesh 同步脚本保持上游原样，组网效果仍需实机确认。

## BE12 Pro 可选功能

- PassWall 版预置手动核心更新命令 `owrt-core-update xray`。更新核心前请备份配置并确认剩余空间。
- daed 版默认不带更新器；如需使用，同时选用 `CONFIG_PACKAGE_owrt-core-update=y` 和 `CONFIG_PACKAGE_upx-arm64-static=y`。
