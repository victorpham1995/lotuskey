#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

echo "=== Cài đặt Bộ gõ LotusKey (IBus Native Wayland) ==="
echo "Thư mục dự án: $ROOT_DIR"

# 1. Compile C-ABI Native Engine
echo "[1/6] Biên dịch Native C IBus Engine..."
cd "$ROOT_DIR"
mkdir -p bin lib include src
ln -sf libLotusKeyCAPI.so "$ROOT_DIR/lib/libLotusKeyCAPI.so.0"

IBUS_INC="$ROOT_DIR/.ibus_dev/usr/include/ibus-1.0"
if [ ! -d "$IBUS_INC" ]; then
    IBUS_INC="/tmp/ibus_dev/usr/include/ibus-1.0"
fi
if [ ! -d "$IBUS_INC" ]; then
    IBUS_INC="/usr/include/ibus-1.0"
fi
if [ ! -d "$IBUS_INC" ]; then
    echo " -> Tự động tải gói header libibus-1.0-dev cục bộ..."
    mkdir -p "$ROOT_DIR/.ibus_dev"
    (cd "$ROOT_DIR/.ibus_dev" && apt-get download libibus-1.0-dev && dpkg-deb -x libibus-1.0-dev*.deb .) || true
    ln -sf /usr/lib/x86_64-linux-gnu/libibus-1.0.so.5 "$ROOT_DIR/.ibus_dev/usr/lib/x86_64-linux-gnu/libibus-1.0.so" 2>/dev/null || true
    IBUS_INC="$ROOT_DIR/.ibus_dev/usr/include/ibus-1.0"
fi

IBUS_LIB_DIR="$ROOT_DIR/.ibus_dev/usr/lib/x86_64-linux-gnu"
if [ ! -f "$IBUS_LIB_DIR/libibus-1.0.so" ]; then
    IBUS_LIB_DIR="/tmp/ibus_dev/usr/lib/x86_64-linux-gnu"
fi
if [ ! -f "$IBUS_LIB_DIR/libibus-1.0.so" ]; then
    IBUS_LIB_DIR="/usr/lib/x86_64-linux-gnu"
fi

gcc -O2 \
  -I"$IBUS_INC" \
  -I"$ROOT_DIR/include" \
  $(pkg-config --cflags gobject-2.0 glib-2.0 gio-2.0) \
  "$ROOT_DIR/src/main.c" \
  -L"$IBUS_LIB_DIR" \
  -L"$ROOT_DIR/lib" \
  -Wl,-rpath,'$ORIGIN' \
  -Wl,-rpath,'$ORIGIN/../lib' \
  -Wl,-rpath,"$ROOT_DIR/lib" \
  -Wl,-rpath,/usr/lib/lotuskey \
  -libus-1.0 \
  $(pkg-config --libs gobject-2.0 glib-2.0 gio-2.0) \
  -lLotusKeyCAPI \
  -o "$ROOT_DIR/bin/ibus-engine-lotuskey"

# Symlink legacy engine name for backwards compatibility
ln -sf ibus-engine-lotuskey "$ROOT_DIR/bin/ibus-engine-lotus"

# 2. Permissions
echo "[2/6] Phân quyền thực thi..."
chmod +x "$ROOT_DIR/bin/ibus-engine-lotuskey"
chmod +x "$ROOT_DIR/bin/lotuskey-menu"
chmod +x "$ROOT_DIR/bin/lotuskey-setup"
chmod +x "$ROOT_DIR/ui/quick_menu.py"
chmod +x "$ROOT_DIR/ui/setup_panel.py"

# Symlinks in ~/.local/bin for CLI invocation
mkdir -p ~/.local/bin
ln -sf "$ROOT_DIR/bin/lotuskey-setup" ~/.local/bin/lotuskey-setup
ln -sf "$ROOT_DIR/bin/lotuskey-menu" ~/.local/bin/lotuskey-menu
ln -sf "$ROOT_DIR/bin/lotuskey-setup" ~/.local/bin/lotuskey

# 3. Copy component XML to user directory
echo "[3/6] Cập nhật IBus Component XML (ibus-LotusKey)..."
mkdir -p ~/.local/share/ibus/component
rm -f ~/.local/share/ibus/component/lotus.xml
cp "$ROOT_DIR/engine/lotus.xml" ~/.local/share/ibus/component/lotuskey.xml

# 4. Desktop Application Entry
echo "[4/6] Cập nhật Application Shortcut..."
mkdir -p ~/.local/share/applications
cat << 'EOF' > ~/.local/share/applications/lotuskey-setup.desktop
[Desktop Entry]
Name=LotusKey - Bảng điều khiển
Comment=Cài đặt kiểu gõ Telex, VNI và phím tắt cho bộ gõ tiếng Việt LotusKey (IBus Wayland)
Exec=/home/victorpham/.gemini/antigravity/scratch/ibus-LotusKey/bin/lotuskey-setup
Icon=/usr/share/icons/hicolor/scalable/apps/fcitx-lotus.svg
Terminal=false
Type=Application
Categories=Settings;Utility;
Keywords=lotus;lotuskey;unikey;vietnamese;telex;vni;ibus;wayland;
EOF

# Also keep compatibility link
ln -sf lotuskey-setup.desktop ~/.local/share/applications/ibus-lotus-setup.desktop

# 5. Initialize config files & Autostart
echo "[5/6] Khởi tạo cấu hình LotusKey & Autostart..."
python3 -c "
import sys, os
sys.path.insert(0, '$ROOT_DIR')
from config.config_manager import load_config, save_config
cfg = load_config()
cfg['autostart'] = True
save_config(cfg)
"

# 6. Update IBus Registry cache & GNOME Sources
echo "[6/6] Đồng bộ IBus Registry Cache & GNOME Input Sources..."
python3 -c "
import os
import gi
gi.require_version('IBus', '1.0')
from gi.repository import IBus

reg = IBus.Registry.new()
reg.load()
reg.load_in_dir(os.path.expanduser('~/.local/share/ibus/component'))
cache_path = os.path.expanduser('~/.cache/ibus/bus/registry')
ok = reg.save_cache_file(cache_path)
if ok:
    print(' -> Đã ghi registry cache thành công:', cache_path)
else:
    print(' -> Cảnh báo: Không thể ghi cache!')
"

gsettings set org.gnome.desktop.input-sources sources "[('ibus', 'lotuskey'), ('xkb', 'us')]"
gsettings set org.gnome.desktop.input-sources mru-sources "[('ibus', 'lotuskey'), ('xkb', 'us')]"
ibus restart
sleep 1
ibus engine lotuskey || ibus engine lotus || true

echo "=== Hoàn tất! Bộ gõ LotusKey đã sẵn sàng hoạt động cùng hệ thống trên GNOME Wayland! ==="
