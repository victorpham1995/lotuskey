#!/usr/bin/env bash
# Builds a Debian/Ubuntu/Mint (.deb) package for LotusKey
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="$(cat "$SCRIPT_DIR/VERSION")"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/dist}"
PKG_NAME="ibus-lotuskey_${VERSION}_${ARCH}"
BUILD_DIR="$(mktemp -d)/${PKG_NAME}"

echo "=== Building Debian Package: ${PKG_NAME}.deb ==="
[ "${SKIP_COMPILE:-0}" = "1" ] || "$SCRIPT_DIR/build_binaries.sh"
"$SCRIPT_DIR/stage_install.sh" "$BUILD_DIR" /lib/udev/rules.d

mkdir -p "$BUILD_DIR/DEBIAN"
cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: ibus-lotuskey
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: ibus, libibus-1.0-5, libc6 (>= 2.35), libglib2.0-0 | libglib2.0-0t64, python3, python3-gi, gir1.2-gtk-3.0
Recommends: gir1.2-ibus-1.0
Suggests: fcitx5
Maintainer: Victor Pham <https://github.com/victorpham1995/lotuskey>
Homepage: https://github.com/victorpham1995/lotuskey
Description: LotusKey Vietnamese Input Method for Linux
 Supports IBus Native C Engine, Fcitx5, Fcitx4, and UInput Kernel Daemon
 with bilingual (Vietnamese/English) user interface.
EOF

cat > "$BUILD_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
command -v ibus >/dev/null 2>&1 && ibus write-cache --system >/dev/null 2>&1 || true
command -v udevadm >/dev/null 2>&1 && udevadm control --reload-rules >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q /usr/share/icons/hicolor >/dev/null 2>&1 || true
exit 0
EOF
cp "$BUILD_DIR/DEBIAN/postinst" "$BUILD_DIR/DEBIAN/postrm"
chmod 755 "$BUILD_DIR/DEBIAN/postinst" "$BUILD_DIR/DEBIAN/postrm"

mkdir -p "$OUT_DIR"
dpkg-deb --root-owner-group --build "$BUILD_DIR" "$OUT_DIR/${PKG_NAME}.deb"
rm -rf "$(dirname "$BUILD_DIR")"
echo "[OK] Built package: $OUT_DIR/${PKG_NAME}.deb"
