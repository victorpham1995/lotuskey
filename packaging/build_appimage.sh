#!/usr/bin/env bash
# Builds a portable LotusKey AppImage (x86_64 / aarch64).
# The AppImage bundles prebuilt binaries + Python UI and uses the host's
# IBus / Python3 / PyGObject / GTK3 at runtime.
#
# Usage of the resulting AppImage:
#   ./LotusKey-<VERSION>-<ARCH>.AppImage              install/update (if needed) and open Settings
#   ./LotusKey-<VERSION>-<ARCH>.AppImage --install    install/update for the current user
#   ./LotusKey-<VERSION>-<ARCH>.AppImage --uninstall  remove the per-user installation
#   ./LotusKey-<VERSION>-<ARCH>.AppImage --menu | --wizard | --setup
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="$(cat "$SCRIPT_DIR/VERSION")"
ARCH="${ARCH:-$(uname -m)}"
case "$ARCH" in
    aarch64|arm64|armv8*) ARCH="aarch64" ;;
    x86_64|amd64|x64)     ARCH="x86_64" ;;
esac
OUT_DIR="${OUT_DIR:-$ROOT_DIR/dist}"
WORK_DIR="$(mktemp -d)"
APPDIR="$WORK_DIR/LotusKey.AppDir"
APP_ROOT="$APPDIR/opt/lotuskey"

echo "=== Building AppImage: LotusKey-${VERSION}-${ARCH}.AppImage ==="
[ "${SKIP_COMPILE:-0}" = "1" ] || "$SCRIPT_DIR/build_binaries.sh"

mkdir -p "$APP_ROOT/bin" "$APP_ROOT/lib"
cp -a "$ROOT_DIR/config" "$ROOT_DIR/ui" "$ROOT_DIR/assets" "$ROOT_DIR/engine" "$ROOT_DIR/include" "$ROOT_DIR/src" "$APP_ROOT/"
find "$APP_ROOT" -name '__pycache__' -prune -exec rm -rf {} +
cp "$ROOT_DIR/install.sh" "$ROOT_DIR/setup.sh" "$ROOT_DIR/README.md" "$APP_ROOT/"
cp "$ROOT_DIR/lib/libLotusKeyCAPI.so" "$APP_ROOT/lib/"
for arch_so in "$ROOT_DIR/lib/"libLotusKeyCAPI-*.so; do
    [ -f "$arch_so" ] && cp "$arch_so" "$APP_ROOT/lib/"
done
ln -sf libLotusKeyCAPI.so "$APP_ROOT/lib/libLotusKeyCAPI.so.0"
for f in ibus-engine-lotuskey lotuskey-uinput lotuskey-setup lotuskey-menu lotuskey-wizard lotuskey-installer lotuskey-autostart; do
    cp "$ROOT_DIR/bin/$f" "$APP_ROOT/bin/"
    chmod 755 "$APP_ROOT/bin/$f"
done
ln -sf ibus-engine-lotuskey "$APP_ROOT/bin/ibus-engine-lotus"
ln -sf lotuskey-setup "$APP_ROOT/bin/lotuskey"
ln -sf lotuskey-setup "$APP_ROOT/bin/ibus-lotus-setup"
ln -sf lotuskey-menu "$APP_ROOT/bin/ibus-lotus-menu"
echo "$VERSION" > "$APP_ROOT/VERSION"
mkdir -p "$APP_ROOT/packaging" && cp "$SCRIPT_DIR/VERSION" "$APP_ROOT/packaging/"

cp "$ROOT_DIR/assets/lotuskey.svg" "$APPDIR/lotuskey.svg"
python3 - "$ROOT_DIR/assets/lotuskey.svg" "$APPDIR/lotuskey.png" <<'PY' 2>/dev/null || true
import sys, gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf
pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(sys.argv[1], 256, 256, True)
pb.savev(sys.argv[2], "png", [], [])
PY
if [ -f "$APPDIR/lotuskey.png" ]; then
    ln -sf lotuskey.png "$APPDIR/.DirIcon"
else
    ln -sf lotuskey.svg "$APPDIR/.DirIcon"
fi
cat > "$APPDIR/lotuskey.desktop" <<'EOF'
[Desktop Entry]
Name=LotusKey
Comment=Vietnamese Input Method for Linux
Comment[vi]=Bộ gõ tiếng Việt cho Linux
Exec=lotuskey
Icon=lotuskey
Terminal=false
Type=Application
Categories=Settings;
X-AppImage-Version=@VERSION@
EOF
sed -i "s/@VERSION@/$VERSION/" "$APPDIR/lotuskey.desktop"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
set -e
HERE="${APPDIR:-$(dirname "$(readlink -f "$0")")}"
SRC="$HERE/opt/lotuskey"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/lotuskey/app"
NEW_VER="$(cat "$SRC/VERSION")"

do_install() {
    echo "[LotusKey] Installing v$NEW_VER to $DEST ..."
    rm -rf "$DEST.new"
    mkdir -p "$(dirname "$DEST")"
    cp -a "$SRC" "$DEST.new"
    chmod -R u+w "$DEST.new"
    rm -rf "$DEST"
    mv "$DEST.new" "$DEST"
    LOTUSKEY_PREBUILT=1 bash "$DEST/install.sh"
}

do_uninstall() {
    if [ "${LOTUSKEY_NO_DAEMON:-0}" != "1" ]; then
        pkill -x ibus-engine-lot 2>/dev/null || true
        pkill -x lotuskey-uinput 2>/dev/null || true
        systemctl --user unset-environment IBUS_COMPONENT_PATH 2>/dev/null || true
    fi
    rm -rf "$DEST"
    rm -f "$HOME/.local/share/ibus/component/lotuskey.xml" \
          "$HOME/.cache/ibus/bus/registry" \
          "$HOME/.local/share/applications/lotuskey-setup.desktop" \
          "$HOME/.local/share/applications/ibus-lotus-setup.desktop" \
          "$HOME/.local/bin/lotuskey" "$HOME/.local/bin/lotuskey-setup" \
          "$HOME/.local/bin/lotuskey-menu" "$HOME/.local/bin/lotuskey-uinput" \
          "$HOME/.local/bin/lotuskey-autostart" "$HOME/.local/bin/lotuskey-wizard" \
          "$HOME/.config/autostart/lotuskey.desktop" \
          "$HOME/.config/environment.d/90-lotuskey-im.conf" \
          "$HOME/.local/share/icons/hicolor/scalable/apps"/lotuskey*.svg
    if [ "${LOTUSKEY_NO_DAEMON:-0}" != "1" ] && { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; }; then
        command -v ibus >/dev/null 2>&1 && ibus restart >/dev/null 2>&1 || true
    fi
    echo "[LotusKey] Uninstalled. Config kept in ~/.config/LotusKey"
}

ensure_installed() {
    if [ ! -f "$DEST/VERSION" ] || [ "$(cat "$DEST/VERSION")" != "$NEW_VER" ]; then
        do_install
    fi
}

case "${1:-}" in
    --install|--silent) do_install ;;
    --uninstall) do_uninstall ;;
    --menu)      ensure_installed; shift; exec "$DEST/bin/lotuskey-menu" "$@" ;;
    --wizard)    ensure_installed; shift; exec "$DEST/bin/lotuskey-wizard" "$@" ;;
    --autostart) ensure_installed; shift; exec "$DEST/bin/lotuskey-autostart" "$@" ;;
    --version|-v) echo "LotusKey $NEW_VER" ;;
    --help|-h)
        echo "LotusKey $NEW_VER AppImage"
        echo "  (no args)    install/update if needed, then open Settings"
        echo "  --install    install/update for the current user"
        echo "  --silent     non-interactive install without launching GUI"
        echo "  --uninstall  remove the per-user installation"
        echo "  --menu       open quick menu"
        echo "  --wizard     open setup wizard"
        echo "  --autostart  run session autostart orchestrator"
        echo "Runtime requirements: ibus, python3, python3-gi (PyGObject), GTK3"
        ;;
    --setup) ensure_installed; shift; exec "$DEST/bin/lotuskey-setup" "$@" ;;
    *)
        ensure_installed
        if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
            exec "$DEST/bin/lotuskey-setup" "$@"
        fi
        ;;
esac
EOF
chmod 755 "$APPDIR/AppRun"

TOOL="${APPIMAGETOOL:-}"
if [ -z "$TOOL" ]; then
    TOOL="$WORK_DIR/appimagetool"
    curl -fsSL -o "$TOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    chmod +x "$TOOL"
fi

mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/LotusKey-${VERSION}-${ARCH}.AppImage"
ARCH="$ARCH" "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUT_FILE"
rm -rf "$WORK_DIR"
echo "[OK] Built AppImage: $OUT_FILE"
