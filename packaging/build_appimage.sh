#!/usr/bin/env bash
# Builds a portable LotusKey AppImage (x86_64).
# The AppImage bundles prebuilt binaries + Python UI and uses the host's
# IBus / Python3 / PyGObject / GTK3 at runtime.
#
# Usage of the resulting AppImage:
#   ./LotusKey-x86_64.AppImage              install/update (if needed) and open Settings
#   ./LotusKey-x86_64.AppImage --install    install/update for the current user
#   ./LotusKey-x86_64.AppImage --uninstall  remove the per-user installation
#   ./LotusKey-x86_64.AppImage --menu | --wizard | --setup
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="$(cat "$SCRIPT_DIR/VERSION")"
ARCH="x86_64"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/dist}"
WORK_DIR="$(mktemp -d)"
APPDIR="$WORK_DIR/LotusKey.AppDir"
APP_ROOT="$APPDIR/opt/lotuskey"

echo "=== Building AppImage: LotusKey-${VERSION}-${ARCH}.AppImage ==="
[ "${SKIP_COMPILE:-0}" = "1" ] || "$SCRIPT_DIR/build_binaries.sh"

mkdir -p "$APP_ROOT/bin" "$APP_ROOT/lib"
cp -a "$ROOT_DIR/config" "$ROOT_DIR/ui" "$ROOT_DIR/assets" "$ROOT_DIR/engine" "$APP_ROOT/"
find "$APP_ROOT" -name '__pycache__' -prune -exec rm -rf {} +
cp "$ROOT_DIR/install.sh" "$ROOT_DIR/setup.sh" "$ROOT_DIR/README.md" "$APP_ROOT/"
cp "$ROOT_DIR/lib/libLotusKeyCAPI.so" "$APP_ROOT/lib/"
ln -sf libLotusKeyCAPI.so "$APP_ROOT/lib/libLotusKeyCAPI.so.0"
for f in ibus-engine-lotuskey lotuskey-uinput lotuskey-setup lotuskey-menu lotuskey-wizard lotuskey-installer; do
    cp "$ROOT_DIR/bin/$f" "$APP_ROOT/bin/"
done
ln -sf ibus-engine-lotuskey "$APP_ROOT/bin/ibus-engine-lotus"
echo "$VERSION" > "$APP_ROOT/VERSION"
mkdir -p "$APP_ROOT/packaging" && cp "$SCRIPT_DIR/VERSION" "$APP_ROOT/packaging/"

cp "$ROOT_DIR/assets/lotuskey.svg" "$APPDIR/lotuskey.svg"
ln -sf lotuskey.svg "$APPDIR/.DirIcon"
cat > "$APPDIR/lotuskey.desktop" <<'EOF'
[Desktop Entry]
Name=LotusKey
Comment=Vietnamese Input Method for Linux
Comment[vi]=Bộ gõ tiếng Việt cho Linux
Exec=lotuskey
Icon=lotuskey
Terminal=false
Type=Application
Categories=Settings;Utility;
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
    pkill -x ibus-engine-lot 2>/dev/null || true
    rm -rf "$DEST"
    rm -f "$HOME/.local/share/ibus/component/lotuskey.xml" \
          "$HOME/.local/share/applications/lotuskey-setup.desktop" \
          "$HOME/.local/share/applications/ibus-lotus-setup.desktop" \
          "$HOME/.local/bin/lotuskey" "$HOME/.local/bin/lotuskey-setup" \
          "$HOME/.local/bin/lotuskey-menu" "$HOME/.local/bin/lotuskey-uinput"
    command -v ibus >/dev/null 2>&1 && ibus restart >/dev/null 2>&1 || true
    echo "[LotusKey] Uninstalled. Config kept in ~/.config/lotuskey"
}

ensure_installed() {
    if [ ! -f "$DEST/VERSION" ] || [ "$(cat "$DEST/VERSION")" != "$NEW_VER" ]; then
        do_install
    fi
}

case "${1:-}" in
    --install)   do_install ;;
    --uninstall) do_uninstall ;;
    --menu)      ensure_installed; shift; exec "$DEST/bin/lotuskey-menu" "$@" ;;
    --wizard)    ensure_installed; shift; exec "$DEST/bin/lotuskey-wizard" "$@" ;;
    --version)   echo "LotusKey $NEW_VER" ;;
    --help|-h)
        echo "LotusKey $NEW_VER AppImage"
        echo "  (no args)    install/update if needed, then open Settings"
        echo "  --install    install/update for the current user"
        echo "  --uninstall  remove the per-user installation"
        echo "  --menu       open quick menu"
        echo "  --wizard     open setup wizard"
        echo "Runtime requirements: ibus, python3, python3-gi (PyGObject), GTK3"
        ;;
    --setup) ensure_installed; shift; exec "$DEST/bin/lotuskey-setup" "$@" ;;
    *)       ensure_installed; exec "$DEST/bin/lotuskey-setup" "$@" ;;
esac
EOF
chmod 755 "$APPDIR/AppRun"

TOOL="${APPIMAGETOOL:-}"
if [ -z "$TOOL" ]; then
    TOOL="$WORK_DIR/appimagetool"
    curl -fsSL -o "$TOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
fi

mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/LotusKey-${VERSION}-${ARCH}.AppImage"
ARCH="$ARCH" "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUT_FILE"
rm -rf "$WORK_DIR"
echo "[OK] Built AppImage: $OUT_FILE"
