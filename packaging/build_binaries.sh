#!/usr/bin/env bash
# Compiles the native LotusKey binaries (IBus engine + UInput daemon) without
# touching the user's desktop session. Used by every packaging target.
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CC_BIN="${CC:-gcc}"
command -v "$CC_BIN" >/dev/null 2>&1 || CC_BIN="cc"

cd "$ROOT_DIR"
mkdir -p bin
ln -sf libLotusKeyCAPI.so lib/libLotusKeyCAPI.so.0

# Prefer the system IBus headers; fall back to the bundled ABI-compatible header.
if pkg-config --exists ibus-1.0 2>/dev/null; then
    IBUS_CFLAGS="$(pkg-config --cflags ibus-1.0)"
    IBUS_LIBS="$(pkg-config --libs ibus-1.0)"
else
    IBUS_CFLAGS="-Iinclude/ibus_fallback $(pkg-config --cflags glib-2.0 gobject-2.0 gio-2.0)"
    IBUS_LIBS="-l:libibus-1.0.so.5 $(pkg-config --libs glib-2.0 gobject-2.0 gio-2.0)"
fi

COMMON_FLAGS="-O2 -s -fno-ident -Wall -Wextra -Wl,--build-id=none -Wl,-z,relro,-z,now"
RPATHS="-Wl,-rpath,\$ORIGIN -Wl,-rpath,\$ORIGIN/../lib -Wl,-rpath,/usr/lib/lotuskey"

# shellcheck disable=SC2086
"$CC_BIN" $COMMON_FLAGS -Iinclude $IBUS_CFLAGS \
    src/main.c \
    -Llib $RPATHS \
    $IBUS_LIBS -lLotusKeyCAPI \
    -o bin/ibus-engine-lotuskey

# shellcheck disable=SC2086
"$CC_BIN" $COMMON_FLAGS -Iinclude \
    src/uinput_daemon.c \
    -Llib $RPATHS -lLotusKeyCAPI \
    -o bin/lotuskey-uinput

if command -v objcopy >/dev/null 2>&1; then
    objcopy --remove-section=.comment --remove-section=.note.gnu.build-id bin/ibus-engine-lotuskey 2>/dev/null || true
    objcopy --remove-section=.comment --remove-section=.note.gnu.build-id bin/lotuskey-uinput 2>/dev/null || true
fi
chmod 755 bin/ibus-engine-lotuskey bin/lotuskey-uinput
echo "[OK] Built bin/ibus-engine-lotuskey and bin/lotuskey-uinput"
