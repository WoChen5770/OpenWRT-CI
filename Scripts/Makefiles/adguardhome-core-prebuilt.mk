include $(TOPDIR)/rules.mk

PKG_NAME:=adguardhome-core-prebuilt
PKG_VERSION:=@AGH_VERSION@
PKG_RELEASE:=1
PKG_SOURCE:=@AGH_SOURCE@
PKG_SOURCE_URL:=https://github.com/AdguardTeam/AdGuardHome/releases/download/@AGH_TAG@
PKG_SOURCE_URL_FILE:=AdGuardHome_linux_arm64.tar.gz
PKG_HASH:=@AGH_HASH@
PKG_LICENSE:=GPL-3.0-only

include $(INCLUDE_DIR)/package.mk

define Package/adguardhome-core-prebuilt
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Official AdGuard Home ARM64 core (UPX compressed)
  URL:=https://github.com/AdguardTeam/AdGuardHome
  DEPENDS:=@aarch64
endef

define Build/Prepare
	$(INSTALL_DIR) $(PKG_BUILD_DIR)
	tar -xzf $(DL_DIR)/$(PKG_SOURCE) -C $(PKG_BUILD_DIR) ./AdGuardHome/AdGuardHome
	upx --best $(PKG_BUILD_DIR)/AdGuardHome/AdGuardHome
	upx -t $(PKG_BUILD_DIR)/AdGuardHome/AdGuardHome
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/adguardhome-core-prebuilt/install
	$(INSTALL_DIR) $(1)/etc/AdGuardHome
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/AdGuardHome/AdGuardHome $(1)/etc/AdGuardHome/AdGuardHome
endef

$(eval $(call BuildPackage,adguardhome-core-prebuilt))
