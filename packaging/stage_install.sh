#!/usr/bin/env bash
# Stages a complete system-wide LotusKey installation into DESTDIR.
# Shared by the .deb, .rpm, Arch, Void, Alpine, Gentoo, Nix, Flatpak and Snap packages.
#   usage: stage_install.sh <DESTDIR> [udev_rules_dir]
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DESTDIR="${1:?usage: stage_install.sh <DESTDIR> [udev_rules_dir]}"
DESTDIR="${DESTDIR%/}"
PREFIX="${PREFIX:-/usr}"
ETCDIR="${ETCDIR:-/etc}"
UDEV_DIR="${2:-$PREFIX/lib/udev/rules.d}"

install -dm755 "$DESTDIR$PREFIX/lib/lotuskey" \
               "$DESTDIR$PREFIX/lib/modules-load.d" \
               "$DESTDIR$PREFIX/share/lotuskey/config" \
               "$DESTDIR$PREFIX/share/lotuskey/ui" \
               "$DESTDIR$PREFIX/share/lotuskey/assets" \
               "$DESTDIR$PREFIX/share/ibus/component" \
               "$DESTDIR$PREFIX/share/icons/hicolor/scalable/apps" \
               "$DESTDIR$PREFIX/share/applications" \
               "$DESTDIR$PREFIX/share/metainfo" \
               "$DESTDIR$PREFIX/bin" \
               "$DESTDIR$ETCDIR/xdg/autostart" \
               "$DESTDIR$UDEV_DIR"

install -m755 "$ROOT_DIR/bin/ibus-engine-lotuskey" "$DESTDIR$PREFIX/lib/lotuskey/"
install -m755 "$ROOT_DIR/bin/lotuskey-uinput" "$DESTDIR$PREFIX/lib/lotuskey/"
install -m755 "$ROOT_DIR/lib/libLotusKeyCAPI.so" "$DESTDIR$PREFIX/lib/lotuskey/"
ln -sf libLotusKeyCAPI.so "$DESTDIR$PREFIX/lib/lotuskey/libLotusKeyCAPI.so.0"

install -m644 "$ROOT_DIR/config/"*.py "$DESTDIR$PREFIX/share/lotuskey/config/"
install -m755 "$ROOT_DIR/ui/"*.py "$DESTDIR$PREFIX/share/lotuskey/ui/"
install -m644 "$ROOT_DIR/assets/"*.svg \
    "$DESTDIR$PREFIX/share/icons/hicolor/scalable/apps/"
install -m644 "$ROOT_DIR/assets/"*.svg \
    "$DESTDIR$PREFIX/share/lotuskey/assets/"
install -m644 "$ROOT_DIR/engine/org.freedesktop.IBus.LotusKey.metainfo.xml" \
    "$DESTDIR$PREFIX/share/metainfo/org.freedesktop.IBus.LotusKey.metainfo.xml"

for pair in "lotuskey-setup:setup_panel.py" "lotuskey-menu:quick_menu.py" "lotuskey-wizard:setup_wizard.py"; do
    name="${pair%%:*}"; script="${pair#*:}"
    printf '#!/usr/bin/env bash\nexec python3 %s/share/lotuskey/ui/%s "$@"\n' "$PREFIX" "$script" > "$DESTDIR$PREFIX/bin/$name"
    chmod 755 "$DESTDIR$PREFIX/bin/$name"
done
install -m755 "$ROOT_DIR/bin/lotuskey-autostart" "$DESTDIR$PREFIX/bin/lotuskey-autostart"
ln -sf lotuskey-setup "$DESTDIR$PREFIX/bin/lotuskey"
ln -sf "$PREFIX/lib/lotuskey/lotuskey-uinput" "$DESTDIR$PREFIX/bin/lotuskey-uinput"

python3 - "$ROOT_DIR" "$DESTDIR" "$PREFIX" <<'PY'
import os, re, sys
root, dest, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, root)
from config.im_framework import generate_ibus_component_xml
xml = generate_ibus_component_xml(f'{prefix}/lib/lotuskey/ibus-engine-lotuskey', f'{prefix}/bin/lotuskey-setup')
xml = re.sub(
    r'<icon>([^<]*)</icon>',
    lambda m: f'<icon>{prefix}/share/icons/hicolor/scalable/apps/{os.path.basename(m.group(1)) if m.group(1).endswith(".svg") else "lotuskey-flag-vn.svg"}</icon>',
    xml,
)
comp_path = f"{dest}{prefix}/share/ibus/component/lotuskey.xml"
with open(comp_path, 'w', encoding='utf-8') as f:
    f.write(xml)
PY

cat > "$DESTDIR$PREFIX/share/applications/lotuskey-setup.desktop" <<EOF
[Desktop Entry]
Name=LotusKey Settings
Name[vi]=LotusKey - Cài đặt
Comment=Vietnamese Input Method for Linux
Comment[vi]=Bộ gõ tiếng Việt cho Linux
Exec=$PREFIX/bin/lotuskey-setup
Icon=lotuskey
Terminal=false
Type=Application
Categories=Settings;Utility;
Keywords=lotus;lotuskey;vietnamese;telex;vni;ibus;fcitx5;wayland;
EOF
chmod 644 "$DESTDIR$PREFIX/share/applications/lotuskey-setup.desktop"

cat > "$DESTDIR$ETCDIR/xdg/autostart/lotuskey.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=LotusKey
Name[vi]=LotusKey - Bộ gõ tiếng Việt
Comment=LotusKey Vietnamese Input Method Autostart
Comment[vi]=Tự động khởi chạy bộ gõ tiếng Việt LotusKey
Exec=$PREFIX/bin/lotuskey-autostart
Icon=lotuskey
Terminal=false
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Phase=Applications
X-KDE-autostart-after=panel
EOF
chmod 644 "$DESTDIR$ETCDIR/xdg/autostart/lotuskey.desktop"

printf 'uinput\n' > "$DESTDIR$PREFIX/lib/modules-load.d/lotuskey-uinput.conf"
chmod 644 "$DESTDIR$PREFIX/lib/modules-load.d/lotuskey-uinput.conf"

cat > "$DESTDIR$UDEV_DIR/99-lotuskey-uinput.rules" <<'EOF'
KERNEL=="uinput", SUBSYSTEM=="misc", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
EOF
chmod 644 "$DESTDIR$UDEV_DIR/99-lotuskey-uinput.rules"

echo "[OK] Staged LotusKey into ${DESTDIR:-/} (PREFIX=$PREFIX, ETCDIR=$ETCDIR)"
