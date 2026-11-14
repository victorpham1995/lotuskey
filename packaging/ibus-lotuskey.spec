%global debug_package %{nil}
%global __arch_install_post %{nil}
%{!?srcroot: %global srcroot %{_sourcedir}/lotuskey}

Name:           ibus-lotuskey
Version:        2.2.1
Release:        1%{?dist}
Summary:        Vietnamese Input Method Engine for Linux (IBus / Fcitx5 / UInput)

License:        MIT
URL:            https://github.com/victorpham1995/lotuskey

BuildRequires:  gcc
BuildRequires:  python3
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  pkgconfig(gobject-2.0)
BuildRequires:  pkgconfig(gio-2.0)
BuildRequires:  pkgconfig(ibus-1.0)
Requires:       ibus
Requires:       python3
%if 0%{?suse_version}
Requires:       python3-gobject
Requires:       python3-gobject-Gdk
Requires:       typelib(Gtk) = 3.0
%else
Requires:       python3-gobject
Requires:       gtk3
%endif

%description
LotusKey is a native Vietnamese input method engine for Linux supporting
IBus, Fcitx5, Fcitx4, and a kernel-level Evdev/UInput daemon across
GNOME, KDE Plasma, Hyprland, Sway, Cinnamon, and XFCE (Wayland & X11).

%build
cd %{srcroot}
packaging/build_binaries.sh

%install
%{srcroot}/packaging/stage_install.sh %{buildroot} /usr/lib/udev/rules.d

%post
ibus write-cache --system >/dev/null 2>&1 || :
udevadm control --reload-rules >/dev/null 2>&1 || :

%postun
ibus write-cache --system >/dev/null 2>&1 || :

%files
/usr/bin/lotuskey
/usr/bin/lotuskey-menu
/usr/bin/lotuskey-setup
/usr/bin/lotuskey-uinput
/usr/bin/lotuskey-wizard
/usr/lib/lotuskey/
/usr/lib/udev/rules.d/99-lotuskey-uinput.rules
/usr/share/lotuskey/
/usr/share/ibus/component/lotuskey.xml
/usr/share/applications/lotuskey-setup.desktop
/usr/share/icons/hicolor/scalable/apps/lotuskey.svg
/usr/share/icons/hicolor/scalable/apps/lotuskey-off.svg

%changelog
* Sat Nov 14 2026 Victor Pham - 2.2.1-1
- Fix IBusEngine ABI layout crash, stale IBus socket and settings panel startup
