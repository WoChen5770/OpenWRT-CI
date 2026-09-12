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

默认管理地址：192.168.123.1。

## X86 虚拟机默认裁剪

`Config/X86.txt` 面向飞牛 / Virtio 虚拟机，在 `GENERAL.txt` 之后加载：

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
