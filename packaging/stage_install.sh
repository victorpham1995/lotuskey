#!/usr/bin/env bash
# Stages a complete system-wide LotusKey installation into DESTDIR.
# Shared by the .deb, .rpm and Arch packages.
#   usage: stage_install.sh <DESTDIR> [udev_rules_dir]
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DESTDIR="${1:?usage: stage_install.sh <DESTDIR> [udev_rules_dir]}"
UDEV_DIR="${2:-/usr/lib/udev/rules.d}"

install -dm755 "$DESTDIR/usr/lib/lotuskey" \
               "$DESTDIR/usr/share/lotuskey/config" \
               "$DESTDIR/usr/share/lotuskey/ui" \
               "$DESTDIR/usr/share/ibus/component" \
               "$DESTDIR/usr/share/icons/hicolor/scalable/apps" \
               "$DESTDIR/usr/share/applications" \
               "$DESTDIR/usr/bin" \
               "$DESTDIR$UDEV_DIR"

install -m755 "$ROOT_DIR/bin/ibus-engine-lotuskey" "$DESTDIR/usr/lib/lotuskey/"
install -m755 "$ROOT_DIR/bin/lotuskey-uinput" "$DESTDIR/usr/lib/lotuskey/"
install -m755 "$ROOT_DIR/lib/libLotusKeyCAPI.so" "$DESTDIR/usr/lib/lotuskey/"
ln -sf libLotusKeyCAPI.so "$DESTDIR/usr/lib/lotuskey/libLotusKeyCAPI.so.0"

install -m644 "$ROOT_DIR/config/"*.py "$DESTDIR/usr/share/lotuskey/config/"
install -m755 "$ROOT_DIR/ui/"*.py "$DESTDIR/usr/share/lotuskey/ui/"
install -m644 "$ROOT_DIR/assets/lotuskey.svg" "$ROOT_DIR/assets/lotuskey-off.svg" \
    "$DESTDIR/usr/share/icons/hicolor/scalable/apps/"

for pair in "lotuskey-setup:setup_panel.py" "lotuskey-menu:quick_menu.py" "lotuskey-wizard:setup_wizard.py"; do
    name="${pair%%:*}"; script="${pair#*:}"
    printf '#!/usr/bin/env bash\nexec python3 /usr/share/lotuskey/ui/%s "$@"\n' "$script" > "$DESTDIR/usr/bin/$name"
    chmod 755 "$DESTDIR/usr/bin/$name"
done
ln -sf lotuskey-setup "$DESTDIR/usr/bin/lotuskey"
ln -sf /usr/lib/lotuskey/lotuskey-uinput "$DESTDIR/usr/bin/lotuskey-uinput"

python3 - "$ROOT_DIR" "$DESTDIR" <<'PY'
import os, sys
root, dest = sys.argv[1], sys.argv[2]
sys.path.insert(0, root)
from config.im_framework import generate_ibus_component_xml
xml = generate_ibus_component_xml('/usr/lib/lotuskey/ibus-engine-lotuskey', '/usr/bin/lotuskey-setup')
import re
xml = re.sub(r'<icon>[^<]*</icon>', '<icon>/usr/share/icons/hicolor/scalable/apps/lotuskey.svg</icon>', xml)
with open(os.path.join(dest, 'usr/share/ibus/component/lotuskey.xml'), 'w', encoding='utf-8') as f:
    f.write(xml)
PY

cat > "$DESTDIR/usr/share/applications/lotuskey-setup.desktop" <<'EOF'
[Desktop Entry]
Name=LotusKey Settings
Name[vi]=LotusKey - Cài đặt
Comment=Vietnamese Input Method for Linux
Comment[vi]=Bộ gõ tiếng Việt cho Linux
Exec=/usr/bin/lotuskey-setup
Icon=lotuskey
Terminal=false
Type=Application
Categories=Settings;Utility;
Keywords=lotus;lotuskey;vietnamese;telex;vni;ibus;fcitx5;wayland;
EOF

cat > "$DESTDIR$UDEV_DIR/99-lotuskey-uinput.rules" <<'EOF'
KERNEL=="uinput", SUBSYSTEM=="misc", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
EOF
chmod 644 "$DESTDIR$UDEV_DIR/99-lotuskey-uinput.rules"

echo "[OK] Staged LotusKey into $DESTDIR"
