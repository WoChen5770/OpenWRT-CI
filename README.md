# 高质量<免费>交流群

[IPQ技术讨论群](https://qm.qq.com/q/v7nMhzB4oU)

# 高质量<付费>中转站

[LiBwrt-Ai](https://api.zipimg.cn/register?aff=LR7FSZ2ZZ4D3)

# 本地编译器

https://github.com/VIKINGYFY/OWRT-Tools.git

# 自用修改版插件

https://github.com/VIKINGYFY/packages.git

# OpenWRT-CI

官方版：

https://github.com/immortalwrt/immortalwrt.git

自用版：

https://github.com/VIKINGYFY/immortalwrt.git

# U-BOOT

高通版-沉心：

https://github.com/chenxin527/uboot-qsdk12.5-build.git

高通版-小猪：

https://github.com/1980490718/u-boot-2016.git

联发科-全新版：

https://github.com/VIKINGYFY/UBOOT-CI/releases

联发科-官方版：

https://drive.wrt.moe/uboot/mediatek

# 固件简要说明

固件每天早上5点自动编译。

固件信息里的时间为编译开始的时间，方便核对上游源码提交时间。

GitHub Actions 默认仅编译 X86 系列固件，不集成 WiFi 驱动。

X86 与 Tenda BE12 Pro 均预置 EasyTier 核心和 LuCI，但不预置 `easytier-web`。

## Tenda BE12 Pro 双版本手动编译

在 Actions 中选择 `TENDA-BE12-PRO`，点击 **Run workflow**；`PROFILE=BOTH` 一次分别构建两版，或选 `PASSWALL` / `DAED` 只构建指定版本，仅选择 `tenda_be12-pro` 设备：

- `TENDA-BE12-PRO-PASSWALL`：保留 PassWall + Xray，不预置 daed/LuCI daed。
- `TENDA-BE12-PRO-DAED`：保留 daed/LuCI daed（含内核 BTF），不预置 PassWall + Xray。

两版共用 `Config/TENDA-BE12-PRO.txt` 中的设备、Wi-Fi 和通用插件配置，并都不预置 `easytier-web`；不照搬 X86 的虚拟机驱动裁剪。编译默认使用 `VIKINGYFY/immortalwrt` 的 `owrt` 分支。可勾选 `TEST` 先只生成配置；正式编译保持 `TEST` 关闭。构建完成后按 Releases 中的版本名下载对应固件，刷机前核对设备型号和镜像类型。此工作流不参与每日自动构建。

PassWall 版与 X86 一样在每次构建时查询 Xray 官方最新发布，并打包官方 ARM64 程序；若最新发布尚无 ARM64 文件，则构建失败而不回退旧版。daed 版不预置 Xray。新版 Xray 可能更大，分包不保证固定的剩余空间。

## BE12 Pro 手动更新核心

新编译的 **PassWall 与 daed 两版**均预置 ARM64 静态 UPX 和 `owrt-core-update`；不会后台自动更新。SSH 登录后按需运行：

```sh
owrt-core-update adguardhome
owrt-core-update xray
```

只有已安装对应核心时才允许更新：daed 版默认没有 Xray，执行 `xray` 子命令会明确报错。AdGuard Home 核心仍由其面板首次安装；更新器不会自动安装核心或修改配置、数据。

脚本从官方 GitHub 发布获取 AdGuard Home 最新稳定版 / Xray 按发布时间最新发布（包括预发布版）的 ARM64 附件，验证发行资产的 SHA256，在 `/tmp` 解包并使用 UPX 压缩和测试。预留临时内存及 overlay 空间后，先在目标目录写入新文件、核对哈希与版本，再替换原核心。运行中的服务会尝试重启，失败时从 `/tmp` 的旧核心副本回滚。若空间或校验不足，直接拒绝替换；**不要重启失败时仍需使用 `/tmp` 备份的设备**。建议事先将重要配置和核心备份到电脑。UPX 运行检查不能代替实际的 DNS / 代理功能测试。

此脚本**不接管 AdGuard Home 自带网页或 LuCI 面板的核心更新按钮**。BE12 Pro 的 flash 空间有限，请勿使用原有页面按钮下载未压缩的新核心；使用上面的手动命令。固件中的 UPX 约 0.6 MiB，但核心更新后写入 `/usr/bin/xray` 或 `/etc/AdGuardHome/AdGuardHome` 的部分仍占用 overlay。X86 固件目前不预置本更新器。

默认管理地址：192.168.123.1。

## X86 虚拟机默认裁剪

`Config/X86.txt` 面向飞牛 / Virtio 虚拟机，在 `GENERAL.txt` 之后加载，并关闭 `TARGET_PER_DEVICE_ROOTFS`，避免设备 profile 通过 `MODULE_DEFAULT_*` 强制选回已裁剪的软件包：

- 不默认集成 USB 网卡、蜂窝网卡、手机 USB 共享网络、音频、USB 存储，以及 Btrfs / exFAT / NTFS / 内核 SMB / FUSE、自动挂载和额外磁盘维护工具。
- 保留 Virtio、直通 PCIe 网卡驱动、AHCI / NVMe、基础 USB / HID 控制台支持，以及启动、`/overlay` 和升级所需的 EXT4 / F2FS / VFAT、基础磁盘工具。
- PassWall 保留 Xray，关闭 Shadowsocks-Rust、ShadowsocksR-Libev、Sing-box、HAProxy 的默认集成及对应 INCLUDE 选项；其他原有插件保持不变。
- 仅改变 X86 默认选包，不删除软件源或软件包定义，不改变其他平台的默认配置。`Config/PRIVATE.txt` 和工作流的 `PACKAGE` 输入仍最后生效，可按需重新选包。

按当前上游包定义，Bandix 和 EasyTier 使用预编译二进制，daed 使用 Go + eBPF；移除 Shadowsocks-Rust 后，默认 X86 选包不再需要它引入的 Rust host / LLVM 编译链。保留 BPF 所需的系统 Clang / LLVM，以及其他平台可能使用的 Rust 编译兼容处理；若手动加入新的 Rust 源码包，仍会需要 Rust 工具链。

# 目录简要说明

workflows——自定义CI配置

Scripts——自定义脚本

Config——自定义配置

#
[![Stargazers over time](https://starchart.cc/VIKINGYFY/OpenWRT-CI.svg?variant=adaptive)](https://starchart.cc/VIKINGYFY/OpenWRT-CI)
