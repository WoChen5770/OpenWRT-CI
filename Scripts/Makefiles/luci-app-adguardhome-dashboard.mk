include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-adguardhome-dashboard
PKG_VERSION:=2.5.6
PKG_RELEASE:=1
PKG_LICENSE:=MIT
PKG_MAINTAINER:=imonior

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-adguardhome-dashboard
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=AdGuard Home LuCI Dashboard
  URL:=https://github.com/imonior/luci-app-adguardhome-dashboard
  DEPENDS:=+luci-base +luci-compat +rpcd +curl +ca-bundle
  PKGARCH:=all
endef

define Package/luci-app-adguardhome-dashboard/description
 LuCI 2.0 dashboard for installing and managing AdGuard Home.
endef

define Build/Compile
endef

define Package/luci-app-adguardhome-dashboard/install
	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/controller
	$(INSTALL_DATA) ./files/luci/controller/adguardhome.lua \
		$(1)/usr/lib/lua/luci/controller/adguardhome.lua

	$(INSTALL_DIR) $(1)/usr/share/luci/menu.d
	$(INSTALL_DATA) ./files/luci/menu.d/luci-app-adguardhome-dashboard.json \
		$(1)/usr/share/luci/menu.d/luci-app-adguardhome-dashboard.json

	$(INSTALL_DIR) $(1)/usr/share/rpcd/acl.d
	$(INSTALL_DATA) ./files/luci/acl.json \
		$(1)/usr/share/rpcd/acl.d/luci-app-adguardhome-dashboard.json

	$(INSTALL_DIR) $(1)/www/luci-static/resources/view/adguardhome
	$(INSTALL_DATA) ./files/view/dashboard.js \
		$(1)/www/luci-static/resources/view/adguardhome/dashboard.js

	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/i18n
	$(INSTALL_DATA) ./files/luci/i18n/adguardhome.po \
		$(1)/usr/lib/lua/luci/i18n/adguardhome.po
	$(INSTALL_DATA) ./files/luci/i18n/adguardhome.zh-cn.po \
		$(1)/usr/lib/lua/luci/i18n/adguardhome.zh-cn.po
	$(INSTALL_DATA) ./files/luci/i18n/adguardhome.lmo \
		$(1)/usr/lib/lua/luci/i18n/adguardhome.lmo
	$(INSTALL_DATA) ./files/luci/i18n/adguardhome.zh-cn.lmo \
		$(1)/usr/lib/lua/luci/i18n/adguardhome.zh-cn.lmo

	$(INSTALL_DIR) $(1)/usr/share/adguardhome-dashboard
	$(INSTALL_DATA) ./manifest.json \
		$(1)/usr/share/adguardhome-dashboard/manifest.json
endef

define Package/luci-app-adguardhome-dashboard/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || {
	rm -rf /tmp/luci-indexcache /tmp/luci-modulecache
	/etc/init.d/rpcd restart >/dev/null 2>&1 || true
	/etc/init.d/uhttpd restart >/dev/null 2>&1 || true
}
exit 0
endef

$(eval $(call BuildPackage,luci-app-adguardhome-dashboard))
