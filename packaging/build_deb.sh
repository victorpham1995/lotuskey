#!/usr/bin/env bash
# Builds a portable Debian/Ubuntu/Mint (.deb) package for LotusKey
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="2.1.0"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
PKG_NAME="ibus-lotuskey_${VERSION}_${ARCH}"
BUILD_DIR="/tmp/${PKG_NAME}"

echo "=== Đóng gói Debian/Ubuntu Package: ${PKG_NAME}.deb ==="
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/lib/lotuskey"
mkdir -p "$BUILD_DIR/usr/share/lotuskey/config"
mkdir -p "$BUILD_DIR/usr/share/lotuskey/ui"
mkdir -p "$BUILD_DIR/usr/share/ibus/component"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/lib/udev/rules.d"

# Ensure binaries are compiled
(cd "$ROOT_DIR" && ./install.sh >/dev/null)

cp "$ROOT_DIR/bin/ibus-engine-lotuskey" "$BUILD_DIR/usr/lib/lotuskey/"
cp "$ROOT_DIR/bin/lotuskey-uinput" "$BUILD_DIR/usr/lib/lotuskey/"
cp "$ROOT_DIR/lib/libLotusKeyCAPI.so" "$BUILD_DIR/usr/lib/lotuskey/"
ln -sf libLotusKeyCAPI.so "$BUILD_DIR/usr/lib/lotuskey/libLotusKeyCAPI.so.0"

cp "$ROOT_DIR/config/"*.py "$BUILD_DIR/usr/share/lotuskey/config/"
cp "$ROOT_DIR/ui/"*.py "$BUILD_DIR/usr/share/lotuskey/ui/"
cp "$ROOT_DIR/assets/lotuskey.svg" "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/"
cp "$ROOT_DIR/assets/lotuskey-off.svg" "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/"

cat > "$BUILD_DIR/usr/bin/lotuskey-setup" << 'EOF'
#!/usr/bin/env bash
exec python3 /usr/share/lotuskey/ui/setup_panel.py "$@"
EOF
chmod 755 "$BUILD_DIR/usr/bin/lotuskey-setup"
ln -sf lotuskey-setup "$BUILD_DIR/usr/bin/lotuskey"

cat > "$BUILD_DIR/usr/bin/lotuskey-menu" << 'EOF'
#!/usr/bin/env bash
exec python3 /usr/share/lotuskey/ui/quick_menu.py "$@"
EOF
chmod 755 "$BUILD_DIR/usr/bin/lotuskey-menu"
ln -sf /usr/lib/lotuskey/lotuskey-uinput "$BUILD_DIR/usr/bin/lotuskey-uinput"

python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.im_framework import generate_ibus_component_xml
xml_str = generate_ibus_component_xml('/usr/lib/lotuskey/ibus-engine-lotuskey', '/usr/bin/lotuskey-setup')
xml_str = xml_str.replace(
    os.path.expanduser('~/.local/share/icons/hicolor/scalable/apps/lotuskey.svg'),
    '/usr/share/icons/hicolor/scalable/apps/lotuskey.svg'
) if 'os' in dir() else xml_str
with open('$BUILD_DIR/usr/share/ibus/component/lotuskey.xml', 'w', encoding='utf-8') as f:
    f.write(xml_str)
"

cat > "$BUILD_DIR/lib/udev/rules.d/99-lotuskey-uinput.rules" << 'EOF'
KERNEL=="uinput", SUBSYSTEM=="misc", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
EOF

cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: ibus-lotuskey
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: ibus, libc6, libglib2.0-0, python3, python3-gi, gir1.2-gtk-3.0
Recommends: fcitx5, gir1.2-gtk-4.0
Maintainer: Victor Pham <https://github.com/victorpham1995/lotuskey>
Description: LotusKey Multi-Framework Vietnamese Input Method for Linux
 Supports IBus Native C Engine, Fcitx5 Adapter, Fcitx4, and Universal UInput Daemon.
EOF

dpkg-deb --root-owner-group --build "$BUILD_DIR" "$ROOT_DIR/${PKG_NAME}.deb"
rm -rf "$BUILD_DIR"
echo "✓ Đã tạo gói: $ROOT_DIR/${PKG_NAME}.deb"
