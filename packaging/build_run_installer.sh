#!/usr/bin/env bash
# Builds a standalone self-extracting executable installer (.run) for LotusKey.
# Works on ANY Linux distribution without requiring FUSE / libfuse2 (unlike AppImage).
#
# Supported flags of the generated .run file:
#   ./LotusKey-<VERSION>-linux-x86_64.run              install/update and open Settings (or silent if headless)
#   ./LotusKey-<VERSION>-linux-x86_64.run --install    install/update for the current user
#   ./LotusKey-<VERSION>-linux-x86_64.run --silent     non-interactive install without launching GUI
#   ./LotusKey-<VERSION>-linux-x86_64.run --wizard     extract & launch interactive GTK Setup Wizard
#   ./LotusKey-<VERSION>-linux-x86_64.run --uninstall  stop daemons and remove per-user installation
#   ./LotusKey-<VERSION>-linux-x86_64.run --system     install system-wide into /usr (requires root)
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
OUT_FILE="$OUT_DIR/LotusKey-${VERSION}-linux-${ARCH}.run"
WORK_DIR="$(mktemp -d)"
STAGE_DIR="$WORK_DIR/lotuskey"
PAYLOAD_TAR="$WORK_DIR/payload.tar.gz"

echo "=== Building Self-Extracting Installer: $(basename "$OUT_FILE") ==="
[ "${SKIP_COMPILE:-0}" = "1" ] || "$SCRIPT_DIR/build_binaries.sh"

mkdir -p "$STAGE_DIR"
cd "$ROOT_DIR"
cp -a assets bin config engine include lib packaging src ui install.sh setup.sh README.md "$STAGE_DIR/"
if [ -f "$ROOT_DIR/flake.nix" ]; then
    cp -a "$ROOT_DIR/flake.nix" "$STAGE_DIR/"
fi
echo "$VERSION" > "$STAGE_DIR/VERSION"
find "$STAGE_DIR" -name '__pycache__' -prune -exec rm -rf {} +

tar -C "$STAGE_DIR" --owner=0 --group=0 -czf "$PAYLOAD_TAR" .

mkdir -p "$OUT_DIR"
cat > "$OUT_FILE" <<'HEADER_EOF'
#!/usr/bin/env sh
# LotusKey Universal Self-Extracting Linux Installer (.run)
# No FUSE / libfuse2 required.
set -e

NEW_VER="@VERSION@"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/lotuskey/app"

extract_payload() {
    target_dir="$1"
    rm -rf "$target_dir"
    mkdir -p "$target_dir"
    archive_line="$(LC_ALL=C awk '/^__LOTUSKEY_ARCHIVE_BELOW__$/ { print NR + 1; exit 0; }' "$0")"
    tail -n +"$archive_line" "$0" | tar -xzf - -C "$target_dir"
    chmod -R u+w "$target_dir"
}

do_install() {
    echo "[LotusKey] Installing LotusKey v$NEW_VER to $DEST ..."
    extract_payload "$DEST.new"
    rm -rf "$DEST"
    mv "$DEST.new" "$DEST"
    LOTUSKEY_PREBUILT=1 bash "$DEST/install.sh"
    echo "[LotusKey] v$NEW_VER installed successfully."
}

do_system_install() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "[ERROR] --system requires root privileges (try: sudo $0 --system)" >&2
        exit 1
    fi
    tmp_sys="$(mktemp -d)"
    extract_payload "$tmp_sys"
    bash "$tmp_sys/packaging/stage_install.sh" "/"
    command -v ibus >/dev/null 2>&1 && ibus write-cache --system >/dev/null 2>&1 || true
    command -v udevadm >/dev/null 2>&1 && udevadm control --reload-rules >/dev/null 2>&1 || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q /usr/share/icons/hicolor >/dev/null 2>&1 || true
    rm -rf "$tmp_sys"
    echo "[LotusKey] System-wide installation v$NEW_VER complete."
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
    echo "[LotusKey] Uninstalled per-user installation. Config preserved in ~/.config/LotusKey"
}

ensure_installed() {
    if [ ! -f "$DEST/VERSION" ] || [ "$(cat "$DEST/VERSION")" != "$NEW_VER" ]; then
        do_install
    fi
}

case "${1:-}" in
    --install|--silent)
        do_install
        ;;
    --system)
        do_system_install
        ;;
    --uninstall)
        do_uninstall
        ;;
    --wizard)
        ensure_installed
        shift
        exec "$DEST/bin/lotuskey-wizard" "$@"
        ;;
    --menu)
        ensure_installed
        shift
        exec "$DEST/bin/lotuskey-menu" "$@"
        ;;
    --setup)
        ensure_installed
        shift
        exec "$DEST/bin/lotuskey-setup" "$@"
        ;;
    --autostart)
        ensure_installed
        shift
        exec "$DEST/bin/lotuskey-autostart" "$@"
        ;;
    --extract)
        out_extract="${2:-./lotuskey-extracted}"
        extract_payload "$out_extract"
        echo "[LotusKey] Extracted payload to $out_extract"
        ;;
    --version|-v)
        echo "LotusKey $NEW_VER"
        ;;
    --help|-h)
        echo "LotusKey $NEW_VER Self-Extracting Linux Installer (.run)"
        echo "Usage:"
        echo "  $0              Install/update and open Settings (if display is active)"
        echo "  $0 --install    Install/update for the current user"
        echo "  $0 --silent     Non-interactive install without launching GUI"
        echo "  $0 --wizard     Install and open interactive GTK Setup Wizard"
        echo "  $0 --setup      Install (if needed) and open Settings panel"
        echo "  $0 --menu       Install (if needed) and open Quick Menu"
        echo "  $0 --autostart  Install (if needed) and run session autostart orchestrator"
        echo "  $0 --system     Install system-wide into /usr (requires root)"
        echo "  $0 --uninstall  Remove per-user installation"
        echo "  $0 --extract D  Extract bundled files into directory D"
        echo "  $0 --version    Print version"
        ;;
    *)
        ensure_installed
        if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
            exec "$DEST/bin/lotuskey-setup" "$@"
        fi
        ;;
esac
exit 0
__LOTUSKEY_ARCHIVE_BELOW__
HEADER_EOF

sed -i "s/@VERSION@/$VERSION/g" "$OUT_FILE"
cat "$PAYLOAD_TAR" >> "$OUT_FILE"
chmod 755 "$OUT_FILE"
rm -rf "$WORK_DIR"
echo "[OK] Built self-extracting installer: $OUT_FILE"
