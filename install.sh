#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

if [ "${1:-}" = "--setup-udev" ]; then
    echo "=== Configuring /dev/uinput permissions for LotusKey ==="
    sudo tee /etc/udev/rules.d/99-lotuskey-uinput.rules >/dev/null << 'EOF'
KERNEL=="uinput", SUBSYSTEM=="misc", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
EOF
    sudo usermod -aG input "$USER" || true
    sudo udevadm control --reload-rules || true
    sudo udevadm trigger || true
    echo "[OK] Configured /etc/udev/rules.d/99-lotuskey-uinput.rules and added '$USER' to 'input' group."
    echo "     Log out and log back in for group changes to take effect."
    exit 0
fi

echo "=== Installing LotusKey ==="

cd "$ROOT_DIR"
mkdir -p bin lib include src

# 1. Verify environment, install SVG icons & check C-ABI library
echo "[1/6] Checking system environment and C-ABI library..."
python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.distro_adapter import DistroAdapter

d = DistroAdapter.detect_distro()
print(f\" -> Distro: {d['name']} ({d['arch']}) | Family: {str(d['family']).upper()} | Package Manager: {d['pkg_manager']}\")
DistroAdapter.install_user_icons('$ROOT_DIR')

ok, msg = DistroAdapter.ensure_capi_library('$ROOT_DIR')
print(f' -> Core Library: {msg}')
if not ok:
    sys.exit(1)
"

ln -sf libLotusKeyCAPI.so "$ROOT_DIR/lib/libLotusKeyCAPI.so.0"

# 2. Compile Native C Engines (IBus + UInput Daemon) with hardened flags
echo "[2/6] Compiling native binaries (ibus-engine-lotuskey & lotuskey-uinput)..."
CC_BIN="${CC:-gcc}"
if ! command -v "$CC_BIN" >/dev/null 2>&1; then
    CC_BIN="cc"
fi

IBUS_CFLAGS_ARR=($(python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.distro_adapter import DistroAdapter
cflags, _ = DistroAdapter.get_ibus_build_flags('$ROOT_DIR')
print(' '.join(cflags))
"))

IBUS_LDFLAGS_ARR=($(python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.distro_adapter import DistroAdapter
_, ldflags = DistroAdapter.get_ibus_build_flags('$ROOT_DIR')
print(' '.join(ldflags))
"))

"$CC_BIN" -O2 -s -fno-ident -Wall -Wextra \
  -Wl,--build-id=none -Wl,-z,relro,-z,now \
  "${IBUS_CFLAGS_ARR[@]}" \
  "$ROOT_DIR/src/main.c" \
  -Wl,-rpath,'$ORIGIN' \
  -Wl,-rpath,'$ORIGIN/../lib' \
  -Wl,-rpath,/usr/lib/lotuskey \
  "${IBUS_LDFLAGS_ARR[@]}" \
  -o "$ROOT_DIR/bin/ibus-engine-lotuskey"

"$CC_BIN" -O2 -s -fno-ident -Wall -Wextra \
  -Wl,--build-id=none -Wl,-z,relro,-z,now \
  -I"$ROOT_DIR/include" \
  "$ROOT_DIR/src/uinput_daemon.c" \
  -L"$ROOT_DIR/lib" \
  -Wl,-rpath,'$ORIGIN' \
  -Wl,-rpath,'$ORIGIN/../lib' \
  -Wl,-rpath,/usr/lib/lotuskey \
  -lLotusKeyCAPI \
  -o "$ROOT_DIR/bin/lotuskey-uinput"

if command -v objcopy >/dev/null 2>&1; then
    objcopy --remove-section=.comment --remove-section=.note.gnu.build-id "$ROOT_DIR/bin/ibus-engine-lotuskey" 2>/dev/null || true
    objcopy --remove-section=.comment --remove-section=.note.gnu.build-id "$ROOT_DIR/bin/lotuskey-uinput" 2>/dev/null || true
fi

ln -sf ibus-engine-lotuskey "$ROOT_DIR/bin/ibus-engine-lotus"

# 3. Permissions & CLI Symlinks
echo "[3/6] Setting permissions and CLI links..."
chmod 755 "$ROOT_DIR/bin/ibus-engine-lotuskey"
chmod 755 "$ROOT_DIR/bin/lotuskey-uinput"
chmod 755 "$ROOT_DIR/bin/lotuskey-menu"
chmod 755 "$ROOT_DIR/bin/lotuskey-setup"
chmod 755 "$ROOT_DIR/bin/lotuskey-installer"
chmod 755 "$ROOT_DIR/bin/lotuskey-wizard"
chmod 755 "$ROOT_DIR/ui/quick_menu.py"
chmod 755 "$ROOT_DIR/ui/setup_panel.py"
chmod 755 "$ROOT_DIR/ui/setup_wizard.py"

mkdir -p ~/.local/bin
ln -sf "$ROOT_DIR/bin/lotuskey-setup" ~/.local/bin/lotuskey-setup
ln -sf "$ROOT_DIR/bin/lotuskey-menu" ~/.local/bin/lotuskey-menu
ln -sf "$ROOT_DIR/bin/lotuskey-uinput" ~/.local/bin/lotuskey-uinput
ln -sf "$ROOT_DIR/bin/lotuskey-setup" ~/.local/bin/lotuskey

# 4. Generate and install IBus Component XML & Desktop Entry
echo "[4/6] Registering IBus component and desktop entry..."
COMP_DIR="$HOME/.local/share/ibus/component"
mkdir -p "$COMP_DIR"
rm -f "$COMP_DIR/lotus.xml"
for sys_xml in /usr/share/ibus/component/*.xml; do
    [ -e "$sys_xml" ] || continue
    base_xml="$(basename "$sys_xml")"
    if [ "$base_xml" != "lotuskey.xml" ] && [ "$base_xml" != "lotus.xml" ]; then
        ln -sf "$sys_xml" "$COMP_DIR/$base_xml"
    fi
done

ICON_PATH="$(python3 -c "
import sys, os
sys.path.insert(0, '$ROOT_DIR')
from config.distro_adapter import DistroAdapter
from config.im_framework import generate_ibus_component_xml
xml_str = generate_ibus_component_xml(
    '$ROOT_DIR/bin/ibus-engine-lotuskey',
    '$ROOT_DIR/bin/lotuskey-setup'
)
comp_xml = os.path.expanduser('~/.local/share/ibus/component/lotuskey.xml')
with open(comp_xml, 'w', encoding='utf-8') as f:
    f.write(xml_str)
print(DistroAdapter.get_icon_path(active=True))
")"

mkdir -p ~/.local/share/applications
cat << EOF > ~/.local/share/applications/lotuskey-setup.desktop
[Desktop Entry]
Name=LotusKey Settings
Name[vi]=LotusKey - Cài đặt
Comment=Vietnamese Input Method for Linux
Comment[vi]=Bộ gõ tiếng Việt cho Linux
Exec=$ROOT_DIR/bin/lotuskey-setup
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Settings;Utility;
Keywords=lotus;lotuskey;vietnamese;telex;vni;ibus;fcitx5;wayland;
EOF

ln -sf lotuskey-setup.desktop ~/.local/share/applications/ibus-lotus-setup.desktop

# 5. Initialize config files, Macros & Multi-Framework Sync
echo "[5/6] Initializing configuration and framework synchronization..."
python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.config_manager import load_config, save_config, load_macros
from config.im_framework import apply_framework_config
cfg = load_config()
macros = load_macros()
cfg['autostart'] = True
save_config(cfg)
eff = apply_framework_config(cfg, macros, switch_daemon=False)
print(' -> Active input backend:', eff.upper())
"

# 6. Update IBus Registry cache & Active IM Backend
echo "[6/6] Updating IBus registry cache and activating engine..."
systemctl --user set-environment IBUS_COMPONENT_PATH="$COMP_DIR" 2>/dev/null || true
IBUS_COMPONENT_PATH="$COMP_DIR" python3 -c "
import os
import gi
gi.require_version('IBus', '1.0')
from gi.repository import IBus

reg = IBus.Registry.new()
reg.load()
cache_path = os.path.expanduser('~/.cache/ibus/bus/registry')
os.makedirs(os.path.dirname(cache_path), exist_ok=True)
ok = reg.save_cache_file(cache_path)
if ok:
    print(' -> Updated IBus registry cache:', cache_path)
" 2>/dev/null || true

pkill -x fcitx5 2>/dev/null || true
pkill -x ibus-engine-lot 2>/dev/null || true
if systemctl --user list-unit-files org.freedesktop.IBus.session.GNOME.service >/dev/null 2>&1; then
    systemctl --user restart org.freedesktop.IBus.session.GNOME.service 2>/dev/null || ibus restart 2>/dev/null || true
elif command -v ibus >/dev/null 2>&1; then
    ibus restart 2>/dev/null || true
fi
sleep 1.5

python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.im_framework import sync_ibus_wayland_socket
sync_ibus_wayland_socket()
" 2>/dev/null || true

if command -v gsettings >/dev/null 2>&1; then
    gsettings set org.gnome.desktop.input-sources sources "[('ibus', 'lotuskey'), ('xkb', 'us')]" 2>/dev/null || true
    gsettings set org.gnome.desktop.input-sources mru-sources "[('ibus', 'lotuskey'), ('xkb', 'us')]" 2>/dev/null || true
fi
if command -v ibus >/dev/null 2>&1; then
    for _ in 1 2 3 4 5; do
        python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.im_framework import sync_ibus_wayland_socket
sync_ibus_wayland_socket()
" 2>/dev/null || true
        if timeout 2 ibus engine lotuskey 2>/dev/null; then
            break
        fi
        sleep 0.6
    done
fi

echo "=== Installation complete ==="
