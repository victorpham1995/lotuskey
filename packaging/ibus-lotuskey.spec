Name:           ibus-lotuskey
Version:        2.2.0
Release:        1%{?dist}
Summary:        Vietnamese Input Method Engine for Linux (IBus / Fcitx5 / UInput)

License:        MIT
URL:            https://github.com/victorpham1995/lotuskey

BuildRequires:  gcc
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  pkgconfig(gobject-2.0)
BuildRequires:  pkgconfig(gio-2.0)
Requires:       ibus
Requires:       python3-gobject
Requires:       gtk3

%description
LotusKey is a native Vietnamese input method engine for Linux supporting
IBus, Fcitx5, Fcitx4, and a kernel-level Evdev/UInput daemon across
GNOME, KDE Plasma, Hyprland, Sway, Cinnamon, and XFCE (Wayland & X11).

%build
ln -sf libLotusKeyCAPI.so lib/libLotusKeyCAPI.so.0

gcc -O2 -s -fno-ident -Wall -Wextra \
    -Wl,--build-id=none -Wl,-z,relro,-z,now \
    -Iinclude -Iinclude/ibus_fallback \
    $(pkg-config --cflags glib-2.0 gobject-2.0 gio-2.0) \
    src/main.c \
    -Llib -Wl,-rpath,/usr/lib/lotuskey \
    -libus-1.0 $(pkg-config --libs glib-2.0 gobject-2.0 gio-2.0) \
    -lLotusKeyCAPI \
    -o bin/ibus-engine-lotuskey

gcc -O2 -s -fno-ident -Wall -Wextra \
    -Wl,--build-id=none -Wl,-z,relro,-z,now \
    -Iinclude src/uinput_daemon.c \
    -Llib -Wl,-rpath,/usr/lib/lotuskey \
    -lLotusKeyCAPI \
    -o bin/lotuskey-uinput

%install
install -dm755 %{buildroot}/usr/lib/lotuskey
install -dm755 %{buildroot}/usr/share/lotuskey/config
install -dm755 %{buildroot}/usr/share/lotuskey/ui
install -dm755 %{buildroot}/usr/share/icons/hicolor/scalable/apps
install -dm755 %{buildroot}/usr/lib/udev/rules.d

install -Dm755 bin/ibus-engine-lotuskey %{buildroot}/usr/lib/lotuskey/ibus-engine-lotuskey
install -Dm755 bin/lotuskey-uinput %{buildroot}/usr/lib/lotuskey/lotuskey-uinput
install -Dm755 lib/libLotusKeyCAPI.so %{buildroot}/usr/lib/lotuskey/libLotusKeyCAPI.so
ln -sf libLotusKeyCAPI.so %{buildroot}/usr/lib/lotuskey/libLotusKeyCAPI.so.0

install -Dm644 config/*.py %{buildroot}/usr/share/lotuskey/config/
install -Dm755 ui/*.py %{buildroot}/usr/share/lotuskey/ui/
install -Dm644 assets/lotuskey.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/lotuskey.svg
install -Dm644 assets/lotuskey-off.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/lotuskey-off.svg

%files
/usr/lib/lotuskey/*
/usr/share/lotuskey/*
/usr/share/icons/hicolor/scalable/apps/lotuskey*.svg
