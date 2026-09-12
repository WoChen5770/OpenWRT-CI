include $(TOPDIR)/rules.mk

PKG_NAME:=xray-core
PKG_VERSION:=@XRAY_VERSION@
PKG_RELEASE:=1

# Resolved for each build, including prereleases. Asset ID avoids stale re-upload caches.
PKG_SOURCE:=Xray-linux-64-$(PKG_VERSION)-@XRAY_ASSET_ID@.zip
PKG_SOURCE_URL:=https://github.com/XTLS/Xray-core/releases/download/@XRAY_TAG@
PKG_SOURCE_URL_FILE:=Xray-linux-64.zip
PKG_HASH:=skip

PKG_LICENSE:=MPL-2.0
PKG_LICENSE_FILES:=LICENSE

include $(INCLUDE_DIR)/package.mk

define Package/xray-core
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Xray core (official x86-64 binary)
  URL:=https://github.com/XTLS/Xray-core
  DEPENDS:=@x86_64 +ca-bundle
endef

define Package/xray-core/description
 Official XTLS x86-64 release, packaged at /usr/bin/xray for PassWall.
 Geodata remains managed by the existing OpenWrt/PassWall packages.
endef

define Build/Prepare
	$(INSTALL_DIR) $(PKG_BUILD_DIR)
	unzip -o $(DL_DIR)/$(PKG_SOURCE) xray LICENSE -d $(PKG_BUILD_DIR)
	test -s $(PKG_BUILD_DIR)/xray
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/xray-core/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/xray $(1)/usr/bin/xray
endef

$(eval $(call BuildPackage,xray-core))
