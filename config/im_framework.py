#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Multi-Framework Linux Input Method Adapter
Supports:
  1. IBus (GNOME, Cinnamon, Budgie, MATE, Unity, XFCE)
  2. Fcitx5 (KDE Plasma, Hyprland, Sway, Cosmic, LXQt, XFCE)
  3. Fcitx4 (Legacy Linux Mint / XFCE)
  4. UInput / Evdev (Universal Kernel-level Daemon for any Wayland/X11 WM)
"""

import glob
import os
import platform
import shutil
import subprocess
from typing import Dict, Any, List
from config.distro_adapter import DistroAdapter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUPPORTED_FRAMEWORKS = [
    ("auto", "Tự động theo Desktop (Auto-detect)"),
    ("ibus", "IBus Native Engine (GNOME / Ubuntu / Mint)"),
    ("fcitx5", "Fcitx5 Framework (KDE Plasma / Hyprland / Sway)"),
    ("fcitx", "Fcitx4 Framework (XFCE / Legacy)"),
    ("uinput", "UInput / Evdev Kernel Daemon (Universal WM)"),
]


def detect_desktop_environment() -> Dict[str, str]:
    """Detects current desktop environment and display server."""
    xdg_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    desktop_session = os.environ.get("DESKTOP_SESSION", "")
    session_type = os.environ.get("XDG_SESSION_TYPE", "")
    if not session_type:
        if os.environ.get("WAYLAND_DISPLAY"):
            session_type = "wayland"
        elif os.environ.get("DISPLAY"):
            session_type = "x11"
        else:
            session_type = "tty"

    gtk_im = os.environ.get("GTK_IM_MODULE", "")
    qt_im = os.environ.get("QT_IM_MODULE", "")
    xmodifiers = os.environ.get("XMODIFIERS", "")

    return {
        "desktop": (xdg_desktop or desktop_session or "Unknown"),
        "session_type": session_type.lower(),
        "gtk_im": gtk_im,
        "qt_im": qt_im,
        "xmodifiers": xmodifiers,
    }


def _is_process_running(proc_pattern: str) -> bool:
    try:
        res = subprocess.run(
            ["pgrep", "-f", proc_pattern],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


def get_uinput_binary() -> str:
    local_bin = os.path.join(BASE_DIR, "bin", "lotuskey-uinput")
    if os.path.isfile(local_bin) and os.access(local_bin, os.X_OK):
        return local_bin
    sys_bin = "/usr/lib/lotuskey/lotuskey-uinput"
    if os.path.isfile(sys_bin) and os.access(sys_bin, os.X_OK):
        return sys_bin
    which_bin = shutil.which("lotuskey-uinput")
    return which_bin or local_bin


def detect_installed_frameworks() -> Dict[str, Dict[str, Any]]:
    """Scans the system for all supported input method frameworks and their status."""
    ibus_bin = shutil.which("ibus") or shutil.which("ibus-daemon")
    fcitx5_bin = shutil.which("fcitx5")
    fcitx4_bin = shutil.which("fcitx")
    uinput_bin = get_uinput_binary()
    uinput_dev = os.path.exists("/dev/uinput") or os.path.exists("/dev/input/uinput")
    uinput_writable = (
        os.access("/dev/uinput", os.W_OK)
        if os.path.exists("/dev/uinput")
        else (os.access("/dev/input/uinput", os.W_OK) if os.path.exists("/dev/input/uinput") else False)
    )

    arch = platform.machine()
    fcitx5_dirs = [
        f"/usr/lib/{arch}-linux-gnu/fcitx5",
        "/usr/lib64/fcitx5",
        "/usr/lib/fcitx5",
        "/run/current-system/sw/lib/fcitx5",
    ]
    fcitx5_lotus_so = any(os.path.exists(os.path.join(d, "liblotus.so")) for d in fcitx5_dirs)
    fcitx5_vn_addon = "lotus" if fcitx5_lotus_so else ""

    return {
        "ibus": {
            "installed": ibus_bin is not None,
            "running": _is_process_running("ibus-daemon"),
            "binary": ibus_bin or "",
            "detail": "IBus Native C Engine (ibus-engine-lotuskey)",
        },
        "fcitx5": {
            "installed": fcitx5_bin is not None,
            "running": _is_process_running("fcitx5"),
            "has_lotus_addon": bool(fcitx5_vn_addon),
            "vn_addon_name": fcitx5_vn_addon or "lotus",
            "binary": fcitx5_bin or "",
            "detail": "Fcitx5 + Lotus Addon" if fcitx5_vn_addon else "Fcitx5 Framework",
        },
        "fcitx": {
            "installed": fcitx4_bin is not None,
            "running": _is_process_running("fcitx") and not _is_process_running("fcitx5"),
            "binary": fcitx4_bin or "",
            "detail": "Fcitx4 Legacy Framework",
        },
        "uinput": {
            "installed": os.path.isfile(uinput_bin) and uinput_dev,
            "running": _is_process_running("lotuskey-uinput"),
            "writable": uinput_writable,
            "binary": uinput_bin,
            "detail": "Evdev/UInput Direct Kernel Daemon",
        },
    }


def resolve_effective_framework(preferred: str = "auto") -> str:
    """Determines which IM backend should be active given user preference and desktop session."""
    frameworks = detect_installed_frameworks()
    if preferred in ("ibus", "fcitx5", "fcitx", "uinput"):
        if frameworks.get(preferred, {}).get("installed", False) or preferred == "uinput":
            return preferred

    env = detect_desktop_environment()
    desktop_lower = env["desktop"].lower()

    # 1. If GNOME, Unity, Cinnamon, Budgie, MATE -> IBus is native
    if any(k in desktop_lower for k in ("gnome", "ubuntu", "unity", "cinnamon", "budgie", "mate", "pantheon")):
        if frameworks["ibus"]["installed"]:
            return "ibus"

    # 2. If KDE, Hyprland, Sway, LXQt, Cosmic -> prefer Fcitx5 if running or installed
    if any(k in desktop_lower for k in ("kde", "plasma", "hyprland", "sway", "lxqt", "cosmic")):
        if frameworks["fcitx5"]["running"] or "fcitx" in env["gtk_im"].lower() or "fcitx" in env["xmodifiers"].lower():
            if frameworks["fcitx5"]["installed"]:
                return "fcitx5"
        if frameworks["ibus"]["running"]:
            return "ibus"
        if frameworks["fcitx5"]["installed"]:
            return "fcitx5"

    # 3. Check currently running daemon
    if frameworks["ibus"]["running"]:
        return "ibus"
    if frameworks["fcitx5"]["running"]:
        return "fcitx5"
    if frameworks["fcitx"]["running"]:
        return "fcitx"
    if frameworks["uinput"]["running"]:
        return "uinput"

    # 4. Fallback to installed framework
    if frameworks["ibus"]["installed"]:
        return "ibus"
    if frameworks["fcitx5"]["installed"]:
        return "fcitx5"
    if frameworks["fcitx"]["installed"]:
        return "fcitx"
    return "uinput"


def generate_ibus_component_xml(engine_exec: str, setup_exec: str) -> str:
    """Generates IBus component XML dynamically without hardcoded developer paths."""
    icon_path = DistroAdapter.get_icon_path(active=True)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!--
    LotusKey (ibus-LotusKey) - IBus Component Specification
    High-performance Native Vietnamese Input Method Engine for Linux Wayland/X11
-->
<component>
    <name>org.freedesktop.IBus.LotusKey</name>
    <description>LotusKey Vietnamese Input Method Engine</description>
    <version>2.2.0</version>
    <author>Victor Pham</author>
    <homepage>https://github.com/victorpham1995/lotuskey</homepage>
    <license>MIT</license>
    <exec>{engine_exec} --ibus</exec>
    <textdomain>ibus-LotusKey</textdomain>
    <observed-paths>
        <path>{engine_exec}</path>
    </observed-paths>
    <engines>
        <engine>
            <name>lotuskey</name>
            <longname>LotusKey - Telex</longname>
            <description>Bộ gõ tiếng Việt LotusKey (Telex / Hybrid)</description>
            <language>vi</language>
            <license>MIT</license>
            <author>Victor Pham</author>
            <icon>{icon_path}</icon>
            <layout>us</layout>
            <rank>99</rank>
            <symbol>VI</symbol>
            <setup>{setup_exec}</setup>
        </engine>
        <engine>
            <name>lotuskey-vni</name>
            <longname>LotusKey - VNI</longname>
            <description>Bộ gõ tiếng Việt LotusKey (VNI)</description>
            <language>vi</language>
            <license>MIT</license>
            <author>Victor Pham</author>
            <icon>{icon_path}</icon>
            <layout>us</layout>
            <rank>98</rank>
            <symbol>VI</symbol>
            <setup>{setup_exec}</setup>
        </engine>
        <engine>
            <name>lotus</name>
            <longname>LotusKey - Telex (Legacy)</longname>
            <description>LotusKey Telex Compatibility Alias</description>
            <language>vi</language>
            <license>MIT</license>
            <author>Victor Pham</author>
            <icon>{icon_path}</icon>
            <layout>us</layout>
            <rank>97</rank>
            <symbol>VI</symbol>
            <setup>{setup_exec}</setup>
        </engine>
        <engine>
            <name>lotus-vni</name>
            <longname>LotusKey - VNI (Legacy)</longname>
            <description>LotusKey VNI Compatibility Alias</description>
            <language>vi</language>
            <license>MIT</license>
            <author>Victor Pham</author>
            <icon>{icon_path}</icon>
            <layout>us</layout>
            <rank>96</rank>
            <symbol>VI</symbol>
            <setup>{setup_exec}</setup>
        </engine>
    </engines>
</component>
"""


def sync_fcitx5_config(cfg: Dict[str, Any], macros: List[Dict[str, str]] = None) -> bool:
    """Synchronizes LotusKey configuration & macros with Fcitx5 (both config files and D-Bus)."""
    try:
        fcitx5_conf_dir = os.path.expanduser("~/.config/fcitx5/conf")
        os.makedirs(fcitx5_conf_dir, exist_ok=True)

        im_idx = cfg.get("input_method", 0)
        im_name = "VNI" if im_idx == 1 else ("Telex + VNI" if im_idx == 2 else "Telex")

        cs_id = cfg.get("charset", 0)
        cs_map = {
            0: "Unicode",
            9: "Unicode tổ hợp",
            31: "Unicode tổ hợp",
            5: "TCVN3 (ABC)",
            27: "TCVN3 (ABC)",
            12: "VNI Windows",
            34: "VNI Windows",
        }
        cs_name = cs_map.get(cs_id, "Unicode")

        bool_str = lambda v: "True" if v else "False"

        conf_content = (
            f"# Generated by LotusKey Multi-Framework Adapter\n"
            f"InputMethod={im_name}\n"
            f"Charset={cs_name}\n"
            f"SpellCheck={bool_str(cfg.get('auto_correct', True))}\n"
            f"AutoNonVnRestore={bool_str(cfg.get('auto_correct', True))}\n"
            f"ModernStyle={bool_str(cfg.get('modern_tone_style', True))}\n"
            f"FreeMarking={bool_str(cfg.get('free_tone_marking', True))}\n"
            f"EnableMacro={bool_str(cfg.get('macro_enabled', True))}\n"
            f"CapitalizeMacro=True\n"
            f"QuickTelex={bool_str(cfg.get('quick_telex', False))}\n"
            f"W2U={bool_str(cfg.get('w2u', True))}\n"
            f"BracketTransform={bool_str(cfg.get('bracket_transform', True))}\n"
            f"PreeditUnderline={bool_str(cfg.get('preedit_underline', False))}\n"
        )
        conf_path = os.path.join(fcitx5_conf_dir, "lotus.conf")
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(conf_content)
        try:
            os.chmod(conf_path, 0o600)
        except OSError:
            pass

        frameworks = detect_installed_frameworks()
        addon_name = frameworks.get("fcitx5", {}).get("vn_addon_name", "lotus")

        # Ensure Fcitx5 profile includes lotus input method
        profile_path = os.path.expanduser("~/.config/fcitx5/profile")
        if not os.path.exists(profile_path):
            profile_content = (
                "[Groups/0]\n"
                "Name=Default\n"
                "Default Layout=us\n"
                f"DefaultIM={addon_name}\n\n"
                "[Groups/0/Items/0]\n"
                "Name=keyboard-us\n"
                "Layout=\n\n"
                "[Groups/0/Items/1]\n"
                f"Name={addon_name}\n"
                "Layout=\n\n"
                "[GroupOrder]\n"
                "0=Default\n"
            )
            with open(profile_path, "w", encoding="utf-8") as f:
                f.write(profile_content)

        # Sync macros to Fcitx5 lotus-macro.conf if provided
        if macros is not None:
            lines = ["# Generated by LotusKey\n"]
            for idx, item in enumerate(macros):
                k = item.get("key", "").strip()
                v = item.get("value", "").strip()
                if k and v:
                    lines.append(f"[Macro/{idx}]\nKey={k}\nValue={v}\n\n")
            macro_conf_path = os.path.join(fcitx5_conf_dir, "lotus-macro.conf")
            with open(macro_conf_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            try:
                os.chmod(macro_conf_path, 0o600)
            except OSError:
                pass

        # If fcitx5 is running, trigger hot-reload and state switch
        if _is_process_running("fcitx5") and shutil.which("fcitx5-remote"):
            subprocess.run(
                ["fcitx5-remote", "-r"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if cfg.get("enabled", True):
                subprocess.run(
                    ["fcitx5-remote", "-s", addon_name],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            else:
                subprocess.run(
                    ["fcitx5-remote", "-c"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        return True
    except Exception as e:
        print(f"Warning syncing Fcitx5 config: {e}")
        return False


def write_im_environment_profile(framework: str) -> None:
    """Writes ~/.config/environment.d/90-lotuskey-im.conf for Wayland/systemd sessions."""
    env_dir = os.path.expanduser("~/.config/environment.d")
    env_file = os.path.join(env_dir, "90-lotuskey-im.conf")
    try:
        os.makedirs(env_dir, exist_ok=True)
        if framework == "fcitx5":
            content = (
                "# Configured by LotusKey\n"
                "GTK_IM_MODULE=fcitx\n"
                "QT_IM_MODULE=fcitx\n"
                "XMODIFIERS=@im=fcitx\n"
                "SDL_IM_MODULE=fcitx\n"
            )
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
        elif framework == "fcitx":
            content = (
                "# Configured by LotusKey\n"
                "GTK_IM_MODULE=fcitx\n"
                "QT_IM_MODULE=fcitx\n"
                "XMODIFIERS=@im=fcitx\n"
            )
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
        elif framework == "ibus":
            content = (
                "# Configured by LotusKey\n"
                "GTK_IM_MODULE=ibus\n"
                "QT_IM_MODULE=ibus\n"
                "XMODIFIERS=@im=ibus\n"
            )
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
        elif os.path.exists(env_file):
            os.remove(env_file)
    except Exception:
        pass


def switch_system_im_framework(framework: str) -> None:
    """
    Configures the active Input Method framework across different Linux distros:
    - Debian/Ubuntu/Mint: im-config
    - Fedora/RHEL/CentOS/Nobara: imsettings-switch
    - KDE Plasma Wayland (Arch/Fedora/openSUSE): kwriteconfig6 / kwriteconfig5 (~/.config/kwinrc)
    - Universal Wayland/Systemd: ~/.config/environment.d/90-lotuskey-im.conf
    """
    write_im_environment_profile(framework)
    if framework not in ("ibus", "fcitx5", "fcitx"):
        return

    # 1. Debian / Ubuntu / Mint (im-config)
    if shutil.which("im-config"):
        subprocess.run(
            ["im-config", "-n", framework],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    # 2. Fedora / RHEL / Nobara (imsettings-switch)
    if shutil.which("imsettings-switch"):
        subprocess.run(
            ["imsettings-switch", "-n", "-q", framework],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    # 3. KDE Plasma Wayland virtual keyboard configuration (Arch, Fedora KDE, openSUSE, Kubuntu)
    env = detect_desktop_environment()
    if any(k in env["desktop"].lower() for k in ("kde", "plasma")):
        kwrite = shutil.which("kwriteconfig6") or shutil.which("kwriteconfig5")
        if kwrite:
            desktop_entry = ""
            if framework == "fcitx5" and os.path.exists("/usr/share/applications/org.fcitx.Fcitx5.desktop"):
                desktop_entry = "/usr/share/applications/org.fcitx.Fcitx5.desktop"
            elif framework == "ibus" and os.path.exists("/usr/share/applications/org.freedesktop.IBus.Panel.Wayland.Gtk3.desktop"):
                desktop_entry = "/usr/share/applications/org.freedesktop.IBus.Panel.Wayland.Gtk3.desktop"
            if desktop_entry:
                subprocess.run(
                    [kwrite, "--file", "kwinrc", "--group", "Wayland", "--key", "InputMethod[$e]", desktop_entry],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )


def apply_framework_config(cfg: Dict[str, Any], macros: List[Dict[str, str]] = None, switch_daemon: bool = False) -> str:
    """
    Synchronizes LotusKey configuration across all Linux IM backends and activates the selected framework.
    Returns the effective framework name ('ibus', 'fcitx5', 'fcitx', or 'uinput').
    """
    preferred = cfg.get("im_framework", "auto")
    effective = resolve_effective_framework(preferred)

    # Always keep Fcitx5 config files in sync if Fcitx5 is installed
    frameworks = detect_installed_frameworks()
    if frameworks["fcitx5"]["installed"]:
        sync_fcitx5_config(cfg, macros)

    if preferred != "auto":
        switch_system_im_framework(effective)
    else:
        write_im_environment_profile(effective)

    if effective == "ibus":
        # Stop uinput daemon if running so keys aren't processed twice
        if frameworks["uinput"]["running"]:
            subprocess.run(["pkill", "-f", "lotuskey-uinput"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        target_engine = "lotuskey-vni" if cfg.get("input_method") == 1 else "lotuskey"
        env = detect_desktop_environment()
        if "gnome" in env["desktop"].lower() or "ubuntu" in env["desktop"].lower():
            if shutil.which("gsettings"):
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.input-sources", "sources", f"[('ibus', '{target_engine}'), ('xkb', 'us')]"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.input-sources", "mru-sources", f"[('ibus', '{target_engine}'), ('xkb', 'us')]"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        if shutil.which("ibus"):
            subprocess.run(["ibus", "engine", target_engine], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-USR1", "-f", "ibus-engine-lotus"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elif effective == "fcitx5":
        if frameworks["uinput"]["running"]:
            subprocess.run(["pkill", "-f", "lotuskey-uinput"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if switch_daemon and not frameworks["fcitx5"]["running"] and shutil.which("fcitx5"):
            subprocess.Popen(["fcitx5", "-r", "-d"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elif effective == "fcitx":
        if frameworks["uinput"]["running"]:
            subprocess.run(["pkill", "-f", "lotuskey-uinput"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if switch_daemon and not frameworks["fcitx"]["running"] and shutil.which("fcitx"):
            subprocess.Popen(["fcitx", "-r", "-d"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elif effective == "uinput":
        uinput_bin = get_uinput_binary()
        if _is_process_running("lotuskey-uinput"):
            subprocess.run(["pkill", "-USR1", "-f", "lotuskey-uinput"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif switch_daemon and os.path.isfile(uinput_bin) and os.access(uinput_bin, os.X_OK):
            subprocess.Popen([uinput_bin, "--daemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return effective
