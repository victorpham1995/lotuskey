#!/usr/bin/env bash
# Compiles the native LotusKey binaries (IBus engine + UInput daemon) without
# touching the user's desktop session. Used by every packaging target.
set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CC_BIN="${CC:-gcc}"
command -v "$CC_BIN" >/dev/null 2>&1 || CC_BIN="cc"

cd "$ROOT_DIR"
mkdir -p bin lib

COMMON_FLAGS="-O2 -s -fno-ident -Wall -Wextra -Wl,--build-id=none -Wl,-z,relro,-z,now"
RPATHS="-Wl,-rpath,\$ORIGIN -Wl,-rpath,\$ORIGIN/../lib -Wl,-rpath,/usr/lib/lotuskey"

TARGET_TRIPLE="$("$CC_BIN" -dumpmachine 2>/dev/null || uname -m)"
TARGET_ARCH="${TARGET_ARCH:-${TARGET_TRIPLE%%-*}}"
case "$TARGET_ARCH" in
    aarch64|arm64|armv8*) TARGET_ARCH="aarch64" ;;
    x86_64|amd64|x64)     TARGET_ARCH="x86_64" ;;
esac

NEED_CAPI_BUILD=0
if [ "${BUILD_CAPI_FROM_SOURCE:-0}" = "1" ] || [ ! -f lib/libLotusKeyCAPI.so ]; then
    NEED_CAPI_BUILD=1
elif [[ "$TARGET_TRIPLE" == *musl* ]]; then
    NEED_CAPI_BUILD=1
else
    CAPI_MATCH="$(python3 -c "
import sys
sys.path.insert(0, '$ROOT_DIR')
from config.distro_adapter import DistroAdapter
print('1' if DistroAdapter.check_binary_arch_compatible('lib/libLotusKeyCAPI.so', '$TARGET_ARCH') else '0')
" 2>/dev/null || echo 0)"
    if [ "$CAPI_MATCH" != "1" ]; then
        NEED_CAPI_BUILD=1
    fi
fi

if [ "$NEED_CAPI_BUILD" = "1" ]; then
    if [ -f src/capi/lotuskey_capi.c ]; then
        echo "[*] Compiling lib/libLotusKeyCAPI.so from source for target: $TARGET_ARCH ($TARGET_TRIPLE)..."
        # shellcheck disable=SC2086
        "$CC_BIN" $COMMON_FLAGS -fPIC -shared \
            -Wl,-soname,libLotusKeyCAPI.so.0 \
            -Iinclude src/capi/lotuskey_capi.c \
            -o lib/libLotusKeyCAPI.so
        if command -v objcopy >/dev/null 2>&1; then
            objcopy --remove-section=.comment --remove-section=.note.gnu.build-id lib/libLotusKeyCAPI.so 2>/dev/null || true
        fi
        chmod 755 lib/libLotusKeyCAPI.so
    elif [ -f "lib/libLotusKeyCAPI-${TARGET_ARCH}.so" ]; then
        cp -f "lib/libLotusKeyCAPI-${TARGET_ARCH}.so" lib/libLotusKeyCAPI.so
        chmod 755 lib/libLotusKeyCAPI.so
    fi
fi

ln -sf libLotusKeyCAPI.so lib/libLotusKeyCAPI.so.0

# Prefer the system IBus headers; fall back to the bundled ABI-compatible header.
if pkg-config --exists ibus-1.0 2>/dev/null; then
    IBUS_CFLAGS="$(pkg-config --cflags ibus-1.0)"
    IBUS_LIBS="$(pkg-config --libs ibus-1.0)"
else
    IBUS_CFLAGS="-Iinclude/ibus_fallback $(pkg-config --cflags glib-2.0 gobject-2.0 gio-2.0)"
    IBUS_LIBS="-l:libibus-1.0.so.5 $(pkg-config --libs glib-2.0 gobject-2.0 gio-2.0)"
fi

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
echo "[OK] Built bin/ibus-engine-lotuskey and bin/lotuskey-uinput ($TARGET_ARCH)"

