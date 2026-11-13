"""
LotusKey - Universal Linux Distribution Adapter
Supports Debian/Ubuntu/Mint, Fedora/RHEL/Nobara, Arch/Manjaro/CachyOS,
openSUSE, Alpine/Void (musl), NixOS, and Immutable Distros (Silverblue/SteamOS)
across x86_64, aarch64, and riscv64.
"""

import ctypes
import glob
import os
import platform
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple


class DistroAdapter:
    """Detects Linux distribution, architecture, libc, and resolves multi-distro paths/packages."""

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

        # Detect immutable systems (Fedora Silverblue/Kinoite, SteamOS, NixOS, openSUSE MicroOS)
        if os.path.exists("/run/ostree-booted") or os.path.exists("/nix/store") or distro_id in ("nixos", "steamos"):
            info["is_immutable"] = True

        # Detect musl libc (Alpine, Void musl, Chimera)
        libc_ver = platform.libc_ver()[0].lower()
        if libc_ver != "glibc" and (glob.glob("/lib/ld-musl-*.so*") or glob.glob("/usr/lib/ld-musl-*.so*")):
            info["is_musl"] = True

        # Detect active package manager binary
        for pm in ("apt-get", "dnf", "rpm-ostree", "pacman", "zypper", "apk", "xbps-install", "nix-env", "emerge"):
            if shutil.which(pm):
                info["pkg_manager"] = pm
                break

        return info

    @classmethod
    def get_install_hint(cls, component: str = "full") -> str:
        """Returns the exact package installation command for the current Linux distribution."""
        d = cls.detect_distro()
        family = d["family"]
        pm = d["pkg_manager"]

        if component == "fcitx5":
            if family == "debian":
                return "sudo apt install -y fcitx5 fcitx5-bamboo fcitx5-config-qt"
            if family == "fedora":
                if pm == "rpm-ostree":
                    return "rpm-ostree install fcitx5 fcitx5-bamboo fcitx5-configtool"
                return "sudo dnf install -y fcitx5 fcitx5-bamboo fcitx5-configtool"
            if family == "arch":
                return "sudo pacman -S --needed fcitx5 fcitx5-bamboo fcitx5-configtool fcitx5-gtk fcitx5-qt"
            if family == "suse":
                return "sudo zypper install -y fcitx5 fcitx5-configtool"
            if family == "alpine":
                return "sudo apk add fcitx5 fcitx5-configtool"
            if family == "void":
                return "sudo xbps-install -S fcitx5 fcitx5-configtool"
            return "Cài đặt gói: fcitx5, fcitx5-lotus (hoặc fcitx5-bamboo)"

        if component == "build":
            if family == "debian":
                return "sudo apt install -y build-essential pkg-config libglib2.0-dev libibus-1.0-dev python3-gi gir1.2-gtk-4.0"
            if family == "fedora":
                return "sudo dnf install -y gcc gcc-c++ pkgconf-pkg-config glib2-devel ibus-devel python3-gobject gtk4"
            if family == "arch":
                return "sudo pacman -S --needed base-devel pkgconf glib2 libibus python-gobject gtk4"
            if family == "suse":
                return "sudo zypper install -y gcc gcc-c++ pkg-config glib2-devel ibus-devel python3-gobject gtk4"
            if family == "alpine":
                return "sudo apk add build-base pkgconf glib-dev ibus-dev py3-gobject3 gtk4.0"
            if family == "void":
                return "sudo xbps-install -S base-devel pkg-config glib-devel ibus-devel python3-gobject gtk4"
            return "Cài đặt: gcc, g++, pkg-config, glib2-devel, python3-gobject, gtk4"

        # Default: runtime + UI dependencies
        if family == "debian":
            return "sudo apt install -y ibus python3-gi gir1.2-gtk-4.0 libglib2.0-dev"
        if family == "fedora":
            return "sudo dnf install -y ibus python3-gobject gtk4 glib2-devel"
        if family == "arch":
            return "sudo pacman -S --needed ibus python-gobject gtk4 glib2"
        if family == "suse":
            return "sudo zypper install -y ibus python3-gobject gtk4 glib2-devel"
        return "Cài đặt: ibus, python3-gobject, gtk4"

    @staticmethod
    def find_shared_library(lib_names: List[str], root_dir: Optional[str] = None) -> Optional[str]:
        """Finds a shared library file across Debian multiarch, Fedora lib64, Arch/Alpine lib, and NixOS."""
        arch = platform.machine()
        search_dirs: List[str] = []

        if root_dir:
            search_dirs.extend([
                os.path.join(root_dir, ".ibus_dev", "usr", "lib", f"{arch}-linux-gnu"),
                os.path.join(root_dir, ".ibus_dev", "usr", "lib64"),
                os.path.join(root_dir, ".ibus_dev", "usr", "lib"),
            ])

        # Try ldconfig -p first (works on Debian, Fedora, Arch, openSUSE, Void)
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
        """
        Returns (cflags, ldflags) to compile src/main.c across any Linux distro,
        automatically falling back to include/ibus_fallback when ibus-devel is absent.
        """
        cflags: List[str] = [f"-I{os.path.join(root_dir, 'include')}"]
        ldflags: List[str] = [
            f"-L{os.path.join(root_dir, 'lib')}",
            "-lLotusKeyCAPI",
            f"-Wl,-rpath,{os.path.join(root_dir, 'lib')}",
        ]

        # 1. Try pkg-config for ibus-1.0 + glib-2.0 + gobject-2.0 + gio-2.0
        if shutil.which("pkg-config"):
            res_full = subprocess.run(
                ["pkg-config", "--cflags", "--libs", "ibus-1.0", "glib-2.0", "gobject-2.0", "gio-2.0"],
                capture_output=True,
                text=True,
            )
            if res_full.returncode == 0:
                tokens = res_full.stdout.strip().split()
                for t in tokens:
                    if t.startswith("-I") or t.startswith("-D") or t.startswith("-pthread"):
                        cflags.append(t)
                    else:
                        ldflags.append(t)
                return cflags, ldflags

            # 2. Try pkg-config for glib-2.0/gobject-2.0/gio-2.0 + our vendored ibus_fallback header
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

        # Add IBus header path (prefer system or .ibus_dev, else vendored include/ibus_fallback)
        dev_ibus_inc = os.path.join(root_dir, ".ibus_dev", "usr", "include", "ibus-1.0")
        if os.path.exists("/usr/include/ibus-1.0/ibus.h"):
            cflags.append("-I/usr/include/ibus-1.0")
        elif os.path.exists(os.path.join(dev_ibus_inc, "ibus.h")):
            cflags.append(f"-I{dev_ibus_inc}")
        else:
            cflags.append(f"-I{os.path.join(root_dir, 'include', 'ibus_fallback')}")

        # Locate libibus-1.0.so.5 or libibus-1.0.so across distros
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
        """Tests if libLotusKeyCAPI.so can be loaded on the current CPU architecture and libc."""
        if not os.path.exists(so_path):
            return False, "File does not exist"
        try:
            lib = ctypes.CDLL(so_path)
            if not hasattr(lib, "lotuskey_create_session"):
                return False, "Missing lotuskey_create_session symbol"
            return True, "OK"
        except OSError as e:
            return False, str(e)

    @classmethod
    def ensure_capi_library(cls, root_dir: str, force_rebuild: bool = False) -> Tuple[bool, str]:
        """
        Verifies that lib/libLotusKeyCAPI.so loads cleanly on the host system.
        If it fails (e.g., GLIBC < 2.38, musl libc, or ARM64/aarch64), automatically
        builds a native lib/libLotusKeyCAPI.so from src/lotuskey_capi_fallback.cpp + core/*.cpp.
        """
        so_path = os.path.join(root_dir, "lib", "libLotusKeyCAPI.so")
        if not force_rebuild:
            ok, reason = cls.check_capi_library_compatible(so_path)
            if ok:
                return True, "Prebuilt libLotusKeyCAPI.so is compatible with host ABI"

        cxx = shutil.which("g++") or shutil.which("clang++") or shutil.which("c++")
        if not cxx:
            return False, "C++ compiler (g++ / clang++) not found to build fallback libLotusKeyCAPI.so"

        fallback_cpp = os.path.join(root_dir, "src", "lotuskey_capi_fallback.cpp")
        core_cpps = sorted(glob.glob(os.path.join(root_dir, "core", "*.cpp")))
        data_cpps = sorted(glob.glob(os.path.join(root_dir, "core", "data", "*.cpp")))

        if not os.path.exists(fallback_cpp) or not core_cpps:
            return False, "Fallback C++ source files missing"

        os.makedirs(os.path.join(root_dir, "lib"), exist_ok=True)
        cmd = [
            cxx,
            "-std=c++20",
            "-O2",
            "-fPIC",
            "-shared",
            f"-I{os.path.join(root_dir, 'include')}",
            f"-I{os.path.join(root_dir, 'core')}",
            fallback_cpp,
            *core_cpps,
            *data_cpps,
            "-o",
            so_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return False, f"Failed to compile fallback libLotusKeyCAPI.so: {res.stderr.strip()}"

        ok, reason = cls.check_capi_library_compatible(so_path)
        if ok:
            return True, "Built native libLotusKeyCAPI.so from source for host architecture/libc"
        return False, reason

    @staticmethod
    def install_user_icons(root_dir: str) -> None:
        """Installs LotusKey SVG icons into ~/.local/share/icons/hicolor/scalable/apps/."""
        assets_dir = os.path.join(root_dir, "assets")
        target_dir = os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps")
        try:
            os.makedirs(target_dir, exist_ok=True)
            on_svg = os.path.join(assets_dir, "lotuskey.svg")
            off_svg = os.path.join(assets_dir, "lotuskey-off.svg")
            if os.path.exists(on_svg):
                shutil.copy2(on_svg, os.path.join(target_dir, "lotuskey.svg"))
                # Also provide fcitx-lotus.svg fallback in user icon theme if system icon is absent
                if not os.path.exists("/usr/share/icons/hicolor/scalable/apps/fcitx-lotus.svg"):
                    shutil.copy2(on_svg, os.path.join(target_dir, "fcitx-lotus.svg"))
            if os.path.exists(off_svg):
                shutil.copy2(off_svg, os.path.join(target_dir, "lotuskey-off.svg"))
                if not os.path.exists("/usr/share/icons/hicolor/scalable/apps/fcitx-lotus-off.svg"):
                    shutil.copy2(off_svg, os.path.join(target_dir, "fcitx-lotus-off.svg"))
        except OSError:
            pass

    @staticmethod
    def get_icon_path(active: bool = True) -> str:
        """Returns the best available icon path on any Linux distribution."""
        user_icon = os.path.expanduser(
            f"~/.local/share/icons/hicolor/scalable/apps/{'lotuskey.svg' if active else 'lotuskey-off.svg'}"
        )
        if os.path.exists(user_icon):
            return user_icon
        sys_icon = f"/usr/share/icons/hicolor/scalable/apps/{'fcitx-lotus.svg' if active else 'fcitx-lotus-off.svg'}"
        if os.path.exists(sys_icon):
            return sys_icon
        return "input-keyboard"
