"""
LotusKey - Linux Distribution Adapter
Supports Debian/Ubuntu/Mint, Fedora/RHEL/Nobara, Arch/Manjaro/CachyOS,
openSUSE, Alpine/Void, and NixOS.
"""

import ctypes
import glob
import os
import platform
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple


class DistroAdapter:
    """Detects Linux distribution and resolves library/header paths."""

    @staticmethod
    def detect_distro() -> Dict[str, object]:
        info: Dict[str, object] = {
            "id": "linux",
            "id_like": "",
            "name": "Linux",
            "version_id": "",
            "family": "unknown",
            "arch": platform.machine(),
            "is_immutable": False,
            "is_musl": False,
            "pkg_manager": "unknown",
        }

        os_release_paths = ["/etc/os-release", "/usr/lib/os-release"]
        raw: Dict[str, str] = {}
        for p in os_release_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if "=" in line and not line.startswith("#"):
                                k, v = line.split("=", 1)
                                raw[k.strip()] = v.strip().strip('"').strip("'")
                    break
                except OSError:
                    pass

        distro_id = raw.get("ID", "linux").lower()
        id_like = raw.get("ID_LIKE", "").lower()
        info["id"] = distro_id
        info["id_like"] = id_like
        info["name"] = raw.get("PRETTY_NAME", raw.get("NAME", "Linux"))
        info["version_id"] = raw.get("VERSION_ID", "")

        combined = f"{distro_id} {id_like}"
        if any(x in combined for x in ("debian", "ubuntu", "mint", "pop", "zorin", "elementary", "kali", "raspbian")):
            info["family"] = "debian"
        elif any(x in combined for x in ("fedora", "rhel", "centos", "rocky", "almalinux", "nobara")):
            info["family"] = "fedora"
        elif any(x in combined for x in ("arch", "manjaro", "endeavouros", "cachyos", "garuda", "artix", "steamos")):
            info["family"] = "arch"
        elif any(x in combined for x in ("suse", "opensuse")):
            info["family"] = "suse"
        elif "alpine" in combined:
            info["family"] = "alpine"
        elif "void" in combined:
            info["family"] = "void"
        elif "nixos" in combined:
            info["family"] = "nixos"
        elif "gentoo" in combined:
            info["family"] = "gentoo"

        if os.path.exists("/run/ostree-booted") or os.path.exists("/nix/store") or distro_id in ("nixos", "steamos"):
            info["is_immutable"] = True

        libc_ver = platform.libc_ver()[0].lower()
        if libc_ver != "glibc" and (glob.glob("/lib/ld-musl-*.so*") or glob.glob("/usr/lib/ld-musl-*.so*")):
            info["is_musl"] = True

        for pm in ("apt-get", "dnf", "rpm-ostree", "pacman", "zypper", "apk", "xbps-install", "nix-env", "emerge"):
            if shutil.which(pm):
                info["pkg_manager"] = pm
                break

        return info

    @classmethod
    def get_install_hint(cls, component: str = "full") -> str:
        d = cls.detect_distro()
        family = d["family"]
        pm = d["pkg_manager"]

        if component == "fcitx5":
            if family == "debian":
                return "sudo apt install -y fcitx5 fcitx5-config-qt"
            if family == "fedora":
                if pm == "rpm-ostree":
                    return "rpm-ostree install fcitx5 fcitx5-configtool"
                return "sudo dnf install -y fcitx5 fcitx5-configtool"
            if family == "arch":
                return "sudo pacman -S --needed fcitx5 fcitx5-configtool fcitx5-gtk fcitx5-qt"
            if family == "suse":
                return "sudo zypper install -y fcitx5 fcitx5-configtool"
            return "fcitx5"

        if component == "build":
            if family == "debian":
                return "sudo apt install -y build-essential pkg-config libglib2.0-dev libibus-1.0-dev python3-gi"
            if family == "fedora":
                return "sudo dnf install -y gcc pkgconf-pkg-config glib2-devel ibus-devel python3-gobject"
            if family == "arch":
                return "sudo pacman -S --needed base-devel pkgconf glib2 libibus python-gobject"
            if family == "suse":
                return "sudo zypper install -y gcc pkg-config glib2-devel ibus-devel python3-gobject"
            return "gcc, pkg-config, glib2-devel, python3-gobject"

        if family == "debian":
            return "sudo apt install -y ibus python3-gi libglib2.0-dev"
        if family == "fedora":
            return "sudo dnf install -y ibus python3-gobject glib2-devel"
        if family == "arch":
            return "sudo pacman -S --needed ibus python-gobject glib2"
        if family == "suse":
            return "sudo zypper install -y ibus python3-gobject glib2-devel"
        return "ibus, python3-gobject"

    @staticmethod
    def find_shared_library(lib_names: List[str], root_dir: Optional[str] = None) -> Optional[str]:
        arch = platform.machine()
        search_dirs: List[str] = []

        if shutil.which("ldconfig"):
            try:
                res = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        for name in lib_names:
                            if name in line and "=>" in line:
                                candidate = line.split("=>", 1)[1].strip()
                                if os.path.exists(candidate):
                                    return candidate
            except Exception:
                pass

        search_dirs.extend([
            f"/usr/lib/{arch}-linux-gnu",
            f"/lib/{arch}-linux-gnu",
            "/usr/lib64",
            "/lib64",
            "/usr/lib",
            "/lib",
            "/usr/local/lib",
            "/run/current-system/sw/lib",
        ])

        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            for name in lib_names:
                exact = os.path.join(d, name)
                if os.path.exists(exact):
                    return exact
                matches = sorted(glob.glob(os.path.join(d, f"{name}*")))
                if matches:
                    return matches[0]
        return None

    @classmethod
    def get_ibus_build_flags(cls, root_dir: str) -> Tuple[List[str], List[str]]:
        cflags: List[str] = [f"-I{os.path.join(root_dir, 'include')}"]
        ldflags: List[str] = [
            f"-L{os.path.join(root_dir, 'lib')}",
            "-lLotusKeyCAPI",
        ]

        if shutil.which("pkg-config"):
            res_full = subprocess.run(
                ["pkg-config", "--cflags", "--libs", "ibus-1.0", "glib-2.0", "gobject-2.0", "gio-2.0"],
                capture_output=True,
                text=True,
            )
            if res_full.returncode == 0:
                for t in res_full.stdout.strip().split():
                    if t.startswith("-I") or t.startswith("-D") or t.startswith("-pthread"):
                        cflags.append(t)
                    else:
                        ldflags.append(t)
                return cflags, ldflags

            res_glib = subprocess.run(
                ["pkg-config", "--cflags", "--libs", "glib-2.0", "gobject-2.0", "gio-2.0"],
                capture_output=True,
                text=True,
            )
            if res_glib.returncode == 0:
                for t in res_glib.stdout.strip().split():
                    if t.startswith("-I") or t.startswith("-D") or t.startswith("-pthread"):
                        cflags.append(t)
                    else:
                        ldflags.append(t)
            else:
                cflags.extend(cls._manual_glib_cflags())
                ldflags.extend(["-lgio-2.0", "-lgobject-2.0", "-lglib-2.0"])
        else:
            cflags.extend(cls._manual_glib_cflags())
            ldflags.extend(["-lgio-2.0", "-lgobject-2.0", "-lglib-2.0"])

        if os.path.exists("/usr/include/ibus-1.0/ibus.h"):
            cflags.append("-I/usr/include/ibus-1.0")
        else:
            cflags.append(f"-I{os.path.join(root_dir, 'include', 'ibus_fallback')}")

        ibus_so = cls.find_shared_library(["libibus-1.0.so", "libibus-1.0.so.5"], root_dir=root_dir)
        if ibus_so:
            ldflags.append(ibus_so)
        else:
            ldflags.append("-libus-1.0")

        return cflags, ldflags

    @staticmethod
    def _manual_glib_cflags() -> List[str]:
        arch = platform.machine()
        inc = ["/usr/include/glib-2.0"]
        for candidate in (
            f"/usr/lib/{arch}-linux-gnu/glib-2.0/include",
            "/usr/lib64/glib-2.0/include",
            "/usr/lib/glib-2.0/include",
        ):
            if os.path.isdir(candidate):
                inc.append(candidate)
                break
        return [f"-I{p}" for p in inc]

    @staticmethod
    def check_capi_library_compatible(so_path: str) -> Tuple[bool, str]:
        if not os.path.exists(so_path):
            return False, "Missing libLotusKeyCAPI.so"
        try:
            lib = ctypes.CDLL(so_path)
            if not hasattr(lib, "lotuskey_create_session"):
                return False, "Invalid symbol table"
            return True, "OK"
        except OSError as e:
            return False, str(e)

    @classmethod
    def ensure_capi_library(cls, root_dir: str) -> Tuple[bool, str]:
        so_path = os.path.join(root_dir, "lib", "libLotusKeyCAPI.so")
        return cls.check_capi_library_compatible(so_path)

    @staticmethod
    def install_user_icons(root_dir: str) -> None:
        assets_dir = os.path.join(root_dir, "assets")
        target_dir = os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps")
        try:
            os.makedirs(target_dir, exist_ok=True)
            on_svg = os.path.join(assets_dir, "lotuskey.svg")
            off_svg = os.path.join(assets_dir, "lotuskey-off.svg")
            if os.path.exists(on_svg):
                shutil.copy2(on_svg, os.path.join(target_dir, "lotuskey.svg"))
            if os.path.exists(off_svg):
                shutil.copy2(off_svg, os.path.join(target_dir, "lotuskey-off.svg"))
        except OSError:
            pass

    @staticmethod
    def get_icon_path(active: bool = True) -> str:
        user_icon = os.path.expanduser(
            f"~/.local/share/icons/hicolor/scalable/apps/{'lotuskey.svg' if active else 'lotuskey-off.svg'}"
        )
        if os.path.exists(user_icon):
            return user_icon
        sys_icon = f"/usr/share/icons/hicolor/scalable/apps/{'lotuskey.svg' if active else 'lotuskey-off.svg'}"
        if os.path.exists(sys_icon):
            return sys_icon
        return "input-keyboard"
