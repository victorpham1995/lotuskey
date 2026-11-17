# Copyright 2026 Gentoo Authors
# Distributed under the terms of the MIT License

EAPI=8

DESCRIPTION="Vietnamese Input Method Engine for Linux (IBus / Fcitx5 / UInput)"
HOMEPAGE="https://github.com/victorpham1995/lotuskey"
SRC_URI="
	amd64? ( https://github.com/victorpham1995/lotuskey/releases/download/v${PV}/lotuskey-${PV}-linux-x86_64.tar.gz )
	arm64? ( https://github.com/victorpham1995/lotuskey/releases/download/v${PV}/lotuskey-${PV}-linux-aarch64.tar.gz )
"
S="${WORKDIR}"

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64 ~arm64"
RESTRICT="strip"

RDEPEND="
	app-i18n/ibus
	dev-lang/python
	dev-libs/glib:2
	dev-python/pygobject:3
	gnome-base/librsvg:2
	x11-libs/gdk-pixbuf:2
	x11-libs/gtk+:3
"
DEPEND="${RDEPEND}"
BDEPEND="
	virtual/pkgconfig
"

QA_PREBUILT="
	usr/lib/lotuskey/libLotusKeyCAPI.so
	usr/lib/lotuskey/ibus-engine-lotuskey
	usr/lib/lotuskey/lotuskey-uinput
"

src_compile() {
	cd "${WORKDIR}"/lotuskey-"${PV}"-linux-* || die
	bash packaging/build_binaries.sh || die
}

src_install() {
	cd "${WORKDIR}"/lotuskey-"${PV}"-linux-* || die
	bash packaging/stage_install.sh "${ED}" /lib/udev/rules.d || die
}
