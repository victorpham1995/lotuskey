#!/usr/bin/env bash
# Builds a distro-agnostic tarball with prebuilt binaries + install.sh
# (works on any glibc >= 2.35 distro: Debian, Ubuntu, Fedora, openSUSE, Arch, Void, Gentoo ...)
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="$(cat "$SCRIPT_DIR/VERSION")"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/dist}"
NAME="lotuskey-${VERSION}-linux-x86_64"
WORK_DIR="$(mktemp -d)"

echo "=== Building generic tarball: ${NAME}.tar.gz ==="
[ "${SKIP_COMPILE:-0}" = "1" ] || "$SCRIPT_DIR/build_binaries.sh"

mkdir -p "$WORK_DIR/$NAME"
cd "$ROOT_DIR"
git ls-files -z 2>/dev/null | xargs -0 -I{} cp --parents -a {} "$WORK_DIR/$NAME/" 2>/dev/null || \
    cp -a assets bin config engine include lib packaging src ui install.sh setup.sh README.md "$WORK_DIR/$NAME/"
cp -a bin/ibus-engine-lotuskey bin/lotuskey-uinput "$WORK_DIR/$NAME/bin/"
find "$WORK_DIR/$NAME" -name '__pycache__' -prune -exec rm -rf {} +

mkdir -p "$OUT_DIR"
tar -C "$WORK_DIR" --owner=0 --group=0 -czf "$OUT_DIR/${NAME}.tar.gz" "$NAME"
rm -rf "$WORK_DIR"
echo "[OK] Built tarball: $OUT_DIR/${NAME}.tar.gz"
