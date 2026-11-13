#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

# Optional flag: ./install.sh --setup-udev (configures /dev/uinput permissions for rootless UInput daemon)
if [ "${1:-}" = "--setup-udev" ]; then
    echo "=== Thiết lập quyền truy cập /dev/uinput cho LotusKey Universal Daemon ==="
    sudo tee /etc/udev/rules.d/99-lotuskey-uinput.rules >/dev/null << 'EOF'
KERNEL=="uinput", SUBSYSTEM=="misc", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
EOF
    sudo usermod -aG input "$USER" || true
    sudo udevadm control --reload-rules || true
    sudo udevadm trigger || true
    echo "✓ Đã cấu hình /etc/udev/rules.d/99-lotuskey-uinput.rules và thêm user '$USER' vào nhóm 'input'."
    echo "  (Lưu ý: Đăng xuất và đăng nhập lại nếu lần đầu thêm vào nhóm 'input')"
    exit 0
fi

echo "=== Cài đặt Bộ gõ LotusKey (Universal Linux Distro & Multi-Framework) ==="
echo "Thư mục dự án: $ROOT_DIR"

cd "$ROOT_DIR"
mkdir -p bin lib include src

# 1. Detect Distro, Install Icons & Verify C-ABI Core Library (Auto-build fallback on ARM64 / musl / older GLIBC)
echo "[1/6] Kiểm tra môi trường Linux Distro, Icon SVG & Thư viện C-ABI Core..."
python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.distro_adapter import DistroAdapter

d = DistroAdapter.detect_distro()
print(f\" -> Hệ điều hành: {d['name']} ({d['arch']}) | Họ distro: {str(d['family']).upper()} | Package Manager: {d['pkg_manager']}\")
DistroAdapter.install_user_icons('$ROOT_DIR')

ok, msg = DistroAdapter.ensure_capi_library('$ROOT_DIR')
print(f' -> Core C-ABI: {msg}')
if not ok:
    print(' -> Gợi ý cài đặt công cụ build:', DistroAdapter.get_install_hint('build'))
    sys.exit(1)
"

ln -sf libLotusKeyCAPI.so "$ROOT_DIR/lib/libLotusKeyCAPI.so.0"

# 2. Compile Native C Engines (IBus + UInput Universal Daemon) using multi-distro flags & fallback headers
echo "[2/6] Biên dịch Native C Engines (ibus-engine-lotuskey & lotuskey-uinput)..."
CC_BIN="${CC:-gcc}"
if ! command -v "$CC_BIN" >/dev/null 2>&1; then
    CC_BIN="cc"
fi

read -r IBUS_CFLAGS IBUS_LDFLAGS < <(python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.distro_adapter import DistroAdapter
cflags, ldflags = DistroAdapter.get_ibus_build_flags('$ROOT_DIR')
print(' '.join(cflags) + '\t' + ' '.join(ldflags))
" | tr '\t' '\n' | paste -sd ' ' -) || true

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

"$CC_BIN" -O2 -Wall -Wextra \
  "${IBUS_CFLAGS_ARR[@]}" \
  "$ROOT_DIR/src/main.c" \
  -Wl,-rpath,'$ORIGIN' \
  -Wl,-rpath,'$ORIGIN/../lib' \
  -Wl,-rpath,"$ROOT_DIR/lib" \
  -Wl,-rpath,/usr/lib/lotuskey \
  "${IBUS_LDFLAGS_ARR[@]}" \
  -o "$ROOT_DIR/bin/ibus-engine-lotuskey"

"$CC_BIN" -O2 -Wall -Wextra \
  -I"$ROOT_DIR/include" \
  "$ROOT_DIR/src/uinput_daemon.c" \
  -L"$ROOT_DIR/lib" \
  -Wl,-rpath,'$ORIGIN' \
  -Wl,-rpath,'$ORIGIN/../lib' \
  -Wl,-rpath,"$ROOT_DIR/lib" \
  -Wl,-rpath,/usr/lib/lotuskey \
  -lLotusKeyCAPI \
  -o "$ROOT_DIR/bin/lotuskey-uinput"

# Symlink legacy engine name for backwards compatibility
ln -sf ibus-engine-lotuskey "$ROOT_DIR/bin/ibus-engine-lotus"

# 3. Permissions & CLI Symlinks
echo "[3/6] Phân quyền thực thi & liên kết CLI..."
chmod +x "$ROOT_DIR/bin/ibus-engine-lotuskey"
chmod +x "$ROOT_DIR/bin/lotuskey-uinput"
chmod +x "$ROOT_DIR/bin/lotuskey-menu"
chmod +x "$ROOT_DIR/bin/lotuskey-setup"
chmod +x "$ROOT_DIR/bin/lotuskey-installer"
chmod +x "$ROOT_DIR/bin/lotuskey-wizard"
chmod +x "$ROOT_DIR/ui/quick_menu.py"
chmod +x "$ROOT_DIR/ui/setup_panel.py"
chmod +x "$ROOT_DIR/ui/setup_wizard.py"

mkdir -p ~/.local/bin
ln -sf "$ROOT_DIR/bin/lotuskey-setup" ~/.local/bin/lotuskey-setup
ln -sf "$ROOT_DIR/bin/lotuskey-menu" ~/.local/bin/lotuskey-menu
ln -sf "$ROOT_DIR/bin/lotuskey-uinput" ~/.local/bin/lotuskey-uinput
ln -sf "$ROOT_DIR/bin/lotuskey-setup" ~/.local/bin/lotuskey

# 4. Generate and install IBus Component XML & Desktop Entry dynamically
echo "[4/6] Cập nhật IBus Component XML, Desktop Entry & Icon..."
mkdir -p ~/.local/share/ibus/component
rm -f ~/.local/share/ibus/component/lotus.xml
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
Name=LotusKey - Bảng điều khiển
Comment=Cài đặt kiểu gõ Telex, VNI, Macro và Multi-Framework (IBus / Fcitx5 / UInput) cho LotusKey
Exec=$ROOT_DIR/bin/lotuskey-setup
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Settings;Utility;
Keywords=lotus;lotuskey;unikey;vietnamese;telex;vni;ibus;fcitx5;wayland;
EOF

ln -sf lotuskey-setup.desktop ~/.local/share/applications/ibus-lotus-setup.desktop

# 5. Initialize config files, Macros & Multi-Distro / Multi-Framework Sync
echo "[5/6] Khởi tạo cấu hình LotusKey, Bảng gõ tắt & Multi-Framework Sync..."
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
print(' -> Hệ thống bộ gõ đang kích hoạt:', eff.upper())
"

# 6. Update IBus Registry cache & Active IM Backend
echo "[6/6] Đồng bộ IBus Registry Cache & Kích hoạt bộ gõ..."
python3 -c "
import os
import gi
gi.require_version('IBus', '1.0')
from gi.repository import IBus

reg = IBus.Registry.new()
reg.load()
reg.load_in_dir(os.path.expanduser('~/.local/share/ibus/component'))
cache_path = os.path.expanduser('~/.cache/ibus/bus/registry')
os.makedirs(os.path.dirname(cache_path), exist_ok=True)
ok = reg.save_cache_file(cache_path)
if ok:
    print(' -> Đã ghi registry cache thành công:', cache_path)
" 2>/dev/null || true

if command -v gsettings >/dev/null 2>&1; then
    gsettings set org.gnome.desktop.input-sources sources "[('ibus', 'lotuskey'), ('xkb', 'us')]" 2>/dev/null || true
    gsettings set org.gnome.desktop.input-sources mru-sources "[('ibus', 'lotuskey'), ('xkb', 'us')]" 2>/dev/null || true
fi
if command -v ibus >/dev/null 2>&1; then
    ibus restart 2>/dev/null || true
    sleep 1
    ibus engine lotuskey 2>/dev/null || ibus engine lotus 2>/dev/null || true
fi

echo "=== Hoàn tất! Bộ gõ LotusKey đã sẵn sàng hoạt động trên mọi bản phân phối Linux! ==="
