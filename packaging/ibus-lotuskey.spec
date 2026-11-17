%global debug_package %{nil}
%global __arch_install_post %{nil}
%{!?srcroot: %global srcroot %{_sourcedir}/lotuskey}

Name:           ibus-lotuskey
Version:        2.3.0
Release:        1%{?dist}
Summary:        Vietnamese Input Method Engine for Linux (IBus / Fcitx5 / UInput)

License:        MIT
URL:            https://github.com/victorpham1995/lotuskey
ExclusiveArch:  x86_64 aarch64

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
Requires:       typelib(GdkPixbuf) = 2.0, gdk-pixbuf-loader-rsvg
%else
Requires:       python3-gobject
Requires:       gtk3
Requires:       gdk-pixbuf2, librsvg2
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
gtk-update-icon-cache -q /usr/share/icons/hicolor >/dev/null 2>&1 || :

%postun
ibus write-cache --system >/dev/null 2>&1 || :
gtk-update-icon-cache -q /usr/share/icons/hicolor >/dev/null 2>&1 || :

%files
%config(noreplace) /etc/xdg/autostart/lotuskey.desktop
/usr/bin/lotuskey
/usr/bin/lotuskey-autostart
/usr/bin/lotuskey-menu
/usr/bin/lotuskey-setup
/usr/bin/lotuskey-uinput
/usr/bin/lotuskey-wizard
/usr/lib/lotuskey/
/usr/lib/modules-load.d/lotuskey-uinput.conf
/usr/lib/udev/rules.d/99-lotuskey-uinput.rules
%dir /usr/share/lotuskey
/usr/share/lotuskey/assets/
/usr/share/lotuskey/config/
/usr/share/lotuskey/ui/
/usr/share/ibus/component/lotuskey.xml
/usr/share/applications/lotuskey-setup.desktop
/usr/share/icons/hicolor/scalable/apps/lotuskey*.svg
/usr/share/metainfo/org.freedesktop.IBus.LotusKey.metainfo.xml

%changelog
* Sat Nov 14 2026 Victor Pham - 2.2.1-1
- Add 9 flat SVG flag/badge/symbolic icons, lotuskey-autostart, AppStream metainfo, and uinput module autoload
- Fix IBusEngine ABI layout crash, stale IBus socket and settings panel startup
