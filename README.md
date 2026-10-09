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

每日 `Auto-Clean` 完成后自动编译 X86、Super Gateway S20P、Tenda BE12 Pro 和小米 BE6500；也可在 Actions 中手动运行相应工作流。BE12 Pro 和 BE6500 均只编译一个 Mesh 版本，不区分 PassWall / daed 版。

| 固件 | 默认内容 |
| --- | --- |
| X86 | 虚拟机适配；PassWall + Xray、EasyTier、AdGuard Home 核心及面板，不集成 WiFi 驱动 |
| S20P | 2GB 内存 + 128GB 存储；PassWall + Xray、daed、honk + LuCI（默认关闭）、Bandix、EasyTier、AdGuard Home 核心及面板、Mesh 组网，保留上游 WiFi 和存储驱动 |
| BE12 Pro | Mesh 组网；默认不集成 UPnP、WOLUltra、PassWall、daed 及 Xray 核心 |
| 小米 BE6500 | 参考 BE12 Pro 的 Mesh 精简配置；保留高通 ath12k 无线驱动、固件和专用校准数据 |

X86 和 S20P 的核心 `adguardhome` 与面板 [`luci-app-adguardhome`](https://github.com/immortalwrt/luci/tree/master/applications/luci-app-adguardhome) 均使用 ImmortalWrt 软件源的原生软件包，不再拉取 `luci-app-adguardhome-dashboard`，也不应用自定义面板 Makefile、补丁或自启脚本。沿用默认二进制 `/usr/bin/AdGuardHome`、配置 `/etc/adguardhome/adguardhome.yaml` 和服务 `/etc/init.d/adguardhome`，不改动 DNS、监听端口或部署路径。

全新配置沿用上游默认的未启用状态，需在 LuCI 的 AdGuard Home 页面勾选“启用”并“保存并应用”；不再强制修改已有配置的启用状态。LuCI 面板管理服务及运行参数，过滤规则、查询日志等仍通过 AdGuard Home 核心自带的 Web 界面配置，不再提供 Dashboard 的在线升级和备份管理入口。

BE12 Pro 和 BE6500 不集成 AdGuard Home 面板或核心，也不执行相关补丁、ARM64 核心预置及数据转存 `/tmp` 的逻辑。Bandix、EasyTier、UPnP、WOLUltra、PassWall、daed、Xray、UPX 和手动核心更新器均默认不集成；仍保留 `Config/PRIVATE.txt` 和工作流 `PACKAGE` 输入供主动选用扩展。基础 LuCI 管理、防火墙、软件包管理、路由角色、FullCone NAT、定时重启及主题保持原有默认。

## S20P

- Actions 工作流：`SUPERGATEWAY-S20P`，配置文件：`Config/SUPERGATEWAY-S20P.txt`，设备标识：`supergateway_s20p`。
- 使用上游 MT7986A / Filogic 设备定义，保留 2GB 内存设置、WiFi、USB、MMC/NVMe 及文件系统支持；不修改 eMMC 分区布局，也不自动扩容到 128GB。
- Xray 使用最新官方 ARM64 二进制（包含预发布版本），不做 UPX 压缩；不预置手动核心更新器，也不把 AdGuard Home 数据转存到 `/tmp`。
- PassWall 默认只使用 Xray，不再编译 Shadowsocks-Rust、ShadowsocksR、Sing-Box、Hysteria、NaiveProxy、Shadow-TLS、HAProxy 及 Shadowsocks 插件后端；保留 Geoview、地理数据和透明代理依赖。独立的 daed、Bandix、EasyTier、AdGuard Home 和 Mesh 不受影响。CI 在 `make defconfig` 后检查被禁用的选项及软件包未重新变为 `y/m`；私有配置或 `PACKAGE` 输入仍可显式覆盖默认裁剪。
- 保留 EasyTier 核心与 LuCI，不额外集成 Web Console。管理地址仍为 `192.168.123.1`。

### honk 试用（仅 S20P）

额外预装 [`189160/luci-app-honk`](https://github.com/189160/luci-app-honk) 的 `honk`、`luci-app-honk` 和中文语言包，**保留 daed 及 `luci-app-daede`，不做替换**。其他机型不拉取或默认集成 honk。

`Scripts/Honk.sh` 固定打包源码提交 `5643dc570baf158b65d0bf7342afd6e15ab305fc`：核心为 `2026.10.9_beta2`（`Glassyiris/honk` 的 `debug.2026.10.9.native-api.2`），LuCI 为 `2.0.0-r3`。沿用上游 ARM64 musl 预编译核心及 `PKG_HASH` 校验，不执行一键安装/自动更新脚本，也不在固件构建中编译 Rust。更新版本需显式修改固定提交并重新核对核心、面板和默认配置。

- 全新配置保留上游 `enabled=0`，native API 配置也保持注释关闭；仅预装，不自动接管流量，不修改 PassWall、daed、AdGuard Home 或 dnsmasq 的配置。升级时保留用户已有的 honk 配置，不强制关闭用户已启用的服务。
- 界面入口为“服务 → HONK”。首次试用需自行配置节点/订阅、路由和 DNS；模板不是开箱即用配置。启用原生面板时需设置认证，优先使用与核心配套的 `ui: 'embedded'`，不要直接把管理接口暴露到 WAN。
- **不要同时启动 honk 与 dae/daed**：它们使用相同的 `dae0` / `daens` 网络资源。试用前先停止 daed，并关闭 PassWall 对同一批流量的透明代理；切回时先正常停止 honk。这里只允许软件包共存，不代表多个透明代理可以同时接管同一网络。
- 保留现有 BTF、XDP 和 eBPF 内核支持，并核对 NFQUEUE、veth、GeoIP/Geosite 依赖。honk 仍是实验性 alpha，首次部署应保留有线管理及回退方式；需实机验证 TCP/UDP、IPv4/IPv6、DNS、重载和停止后的网络恢复。

## Mesh 组网（S20P / BE12 Pro / BE6500）

S20P、BE12 Pro 和 BE6500 默认集成 [xxosdev/luci-app-mesh](https://github.com/xxosdev/luci-app-mesh) 的 `main` 分支，配套 802.11s、batman-adv、`batctl-default`、LuCI batman-adv 协议支持及 DAWN/umdns。X86 不集成。构建时仅把插件的 `wpad-mesh-openssl` 依赖改为 Filogic / qualcommbe 默认的完整 `wpad-openssl`（已包含 Mesh/SAE），避免两个互斥版本同时安装；界面、服务脚本和默认配置不修改。

保留上游 `enabled=0`：仅预装，不自动组网。刷入后在“网络 → Mesh 组网”检查无线能力并配置角色、Mesh ID 和密码。启用子节点会由插件合并 WAN/LAN、关闭本机 DHCP，并改为从主节点获取管理地址；操作前请备份配置并留意回滚确认提示。

已知兼容限制：上游 `meshctl` 的配置同步请求固定使用 HTTP，且 `curl` 未开启跟随跳转。本仓库默认不强制跳转；若手动开启 HTTP → HTTPS 跳转或关闭 HTTP 监听，子节点自动同步可能失败。Mesh 同步脚本保持上游原样，组网效果仍需实机确认。

## BE12 Pro 构建

- Actions 工作流：`TENDA-BE12-PRO`，配置文件：`Config/TENDA-BE12-PRO.txt`。
- 默认只构建 Mesh 版，不下载官方 Xray 二进制，不安装构建主机 UPX，也不预置设备端 UPX 或核心更新器。
- CI 会在 `make defconfig` 后核对 Mesh 依赖，并检查默认关闭的软件包没有被依赖重新选中；主动使用私有配置或 `PACKAGE` 输入时允许覆盖默认裁剪。

## 小米 BE6500 构建

- Actions 工作流：`XIAOMI-BE6500`，配置文件：`Config/XIAOMI-BE6500.txt`；与 BE12 Pro 一样支持每日自动构建和手动 `PACKAGE` 输入，使用独立缓存及 Release 标签。
- 使用[上游 BE6500 设备定义](https://github.com/VIKINGYFY/immortalwrt/blob/owrt/target/linux/qualcommbe/image/ipq53xx.mk)：`qualcommbe/ipq53xx`、`xiaomi_be6500`（IPQ5312）。不修改设备树或 NAND/UBI 分区布局，不使用 BE12 Pro 的 Filogic 设备配置。
- 插件裁剪、Mesh 依赖、主题和默认管理地址均参考 BE12 Pro；保留 `kmod-qcom-ppe`、`kmod-ath12k`、上游 IPQ5332/QCN9274 固件及 `ipq-wifi-xiaomi_be6500`，CI 会检查这些必要组件。
- Mesh 仅预装，默认不启用；无线频段组合、漫游及组网稳定性仍需实机验证。这是 OpenWrt 的 802.11s/batman-adv 方案，不保证兼容小米原厂一键 Mesh。
