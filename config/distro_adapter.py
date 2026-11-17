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

    ELF_MACHINE_MAP = {
        "x86_64": 62,       # EM_X86_64
        "aarch64": 183,     # EM_AARCH64
        "riscv64": 243,     # EM_RISCV
        "armv7l": 40,       # EM_ARM
        "ppc64le": 21,      # EM_PPC64
        "loongarch64": 258, # EM_LOONGARCH
    }

    @staticmethod
    def normalize_arch(arch: Optional[str] = None) -> str:
        raw = (arch or platform.machine() or "").strip().lower()
        if raw in ("aarch64", "arm64", "armv8b", "armv8l"):
            return "aarch64"
        if raw in ("x86_64", "amd64", "x64"):
            return "x86_64"
        return raw

    @staticmethod
    def get_elf_machine(path: str) -> Optional[int]:
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "rb") as f:
                hdr = f.read(20)
            if len(hdr) < 20 or hdr[:4] != b"\x7fELF":
                return None
            return int.from_bytes(hdr[18:20], byteorder="little" if hdr[5] == 1 else "big")
        except OSError:
            return None

    @classmethod
    def check_binary_arch_compatible(cls, bin_path: str, target_arch: Optional[str] = None) -> bool:
        if not os.path.isfile(bin_path) or not os.access(bin_path, os.X_OK):
            return False
        em = cls.get_elf_machine(bin_path)
        if em is None:
            return False
        norm = cls.normalize_arch(target_arch)
        expected = cls.ELF_MACHINE_MAP.get(norm)
        if expected is not None:
            return em == expected
        return True

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
    def build_capi_library(cls, root_dir: str, cc_bin: Optional[str] = None) -> Tuple[bool, str]:
        capi_src = os.path.join(root_dir, "src", "capi", "lotuskey_capi.c")
        if not os.path.isfile(capi_src):
            return False, f"Missing C-ABI source file: {capi_src}"

        compiler = (
            cc_bin
            or os.environ.get("CC")
            or shutil.which("gcc")
            or shutil.which("clang")
            or shutil.which("cc")
        )
        if not compiler:
            return False, "No C compiler (gcc/clang/cc) found to build libLotusKeyCAPI.so"

        lib_dir = os.path.join(root_dir, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        so_path = os.path.join(lib_dir, "libLotusKeyCAPI.so")
        tmp_so = f"{so_path}.tmp.{os.getpid()}"
        inc_dir = os.path.join(root_dir, "include")

        cmd = [
            compiler,
            "-O2", "-s", "-fno-ident", "-fPIC", "-shared",
            "-Wall", "-Wextra",
            "-Wl,--build-id=none", "-Wl,-z,relro,-z,now",
            "-Wl,-soname,libLotusKeyCAPI.so.0",
            f"-I{inc_dir}",
            capi_src,
            "-o", tmp_so,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0 or not os.path.isfile(tmp_so):
            try:
                if os.path.exists(tmp_so):
                    os.remove(tmp_so)
            except OSError:
                pass
            return False, f"Failed to compile libLotusKeyCAPI.so: {res.stderr.strip()}"

        os.chmod(tmp_so, 0o755)
        os.replace(tmp_so, so_path)
        so0_link = os.path.join(lib_dir, "libLotusKeyCAPI.so.0")
        try:
            if os.path.exists(so0_link) or os.path.islink(so0_link):
                os.remove(so0_link)
            os.symlink("libLotusKeyCAPI.so", so0_link)
        except OSError:
            pass
        return True, f"Compiled libLotusKeyCAPI.so from source ({cls.normalize_arch()})"

    @classmethod
    def ensure_capi_library(cls, root_dir: str) -> Tuple[bool, str]:
        lib_dir = os.path.join(root_dir, "lib")
        so_path = os.path.join(lib_dir, "libLotusKeyCAPI.so")
        norm_arch = cls.normalize_arch()

        if os.environ.get("BUILD_CAPI_FROM_SOURCE") == "1":
            built_ok, built_msg = cls.build_capi_library(root_dir)
            if built_ok:
                ok, reason = cls.check_capi_library_compatible(so_path)
                if ok:
                    return True, built_msg
                return False, reason
            return False, built_msg

        ok, reason = cls.check_capi_library_compatible(so_path)
        if ok:
            so0_link = os.path.join(lib_dir, "libLotusKeyCAPI.so.0")
            if not os.path.exists(so0_link):
                try:
                    os.symlink("libLotusKeyCAPI.so", so0_link)
                except OSError:
                    pass
            return True, "OK"

        # Incompatible or missing (e.g. x86_64 .so on aarch64 host): compile from source first
        built_ok, built_msg = cls.build_capi_library(root_dir)
        if built_ok:
            ok2, _ = cls.check_capi_library_compatible(so_path)
            if ok2:
                return True, built_msg

        # Fallback to architecture-specific prebuilt library if available
        arch_prebuilt = os.path.join(lib_dir, f"libLotusKeyCAPI-{norm_arch}.so")
        if os.path.isfile(arch_prebuilt):
            try:
                shutil.copy2(arch_prebuilt, so_path)
                os.chmod(so_path, 0o755)
                ok3, _ = cls.check_capi_library_compatible(so_path)
                if ok3:
                    return True, f"Activated prebuilt libLotusKeyCAPI-{norm_arch}.so"
            except OSError:
                pass

        return False, reason

    ICON_FILES = (
        "lotuskey.svg",
        "lotuskey-off.svg",
        "lotuskey-flag-vn.svg",
        "lotuskey-flag-us.svg",
        "lotuskey-flag-uk.svg",
        "lotuskey-badge-vn.svg",
        "lotuskey-badge-en.svg",
        "lotuskey-symbolic.svg",
        "lotuskey-off-symbolic.svg",
    )

    @classmethod
    def install_user_icons(cls, root_dir: str) -> None:
        assets_dir = os.path.join(root_dir, "assets")
        target_dir = os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps")
        try:
            os.makedirs(target_dir, exist_ok=True)
            for fname in cls.ICON_FILES:
                src_svg = os.path.join(assets_dir, fname)
                if os.path.exists(src_svg):
                    shutil.copy2(src_svg, os.path.join(target_dir, fname))
        except OSError:
            pass

    @staticmethod
    def resolve_icon_filename(active: bool = True, icon_style: str = "flag", flag_variant: str = "us") -> str:
        style = (icon_style or "flag").lower()
        variant = (flag_variant or "us").lower()
        if style == "badge":
            return "lotuskey-badge-vn.svg" if active else "lotuskey-badge-en.svg"
        if style == "lotus":
            return "lotuskey.svg" if active else "lotuskey-off.svg"
        if style == "symbolic":
            return "lotuskey-symbolic.svg" if active else "lotuskey-off-symbolic.svg"
        if active:
            return "lotuskey-flag-vn.svg"
        return "lotuskey-flag-uk.svg" if variant == "uk" else "lotuskey-flag-us.svg"

    @classmethod
    def get_status_icon_path(cls, active: bool = True, icon_style: str = "flag", flag_variant: str = "us") -> str:
        fname = cls.resolve_icon_filename(active=active, icon_style=icon_style, flag_variant=flag_variant)
        user_icon = os.path.expanduser(f"~/.local/share/icons/hicolor/scalable/apps/{fname}")
        if os.path.exists(user_icon):
            return user_icon
        sys_icon = f"/usr/share/icons/hicolor/scalable/apps/{fname}"
        if os.path.exists(sys_icon):
            return sys_icon
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        asset_icon = os.path.join(base_dir, "assets", fname)
        if os.path.exists(asset_icon):
            return asset_icon
        return cls.get_icon_path(active=active)

    @classmethod
    def get_icon_path(cls, active: bool = True, icon_style: Optional[str] = None, flag_variant: str = "us") -> str:
        if icon_style:
            return cls.get_status_icon_path(active=active, icon_style=icon_style, flag_variant=flag_variant)
        fname = "lotuskey.svg" if active else "lotuskey-off.svg"
        user_icon = os.path.expanduser(f"~/.local/share/icons/hicolor/scalable/apps/{fname}")
        if os.path.exists(user_icon):
            return user_icon
        sys_icon = f"/usr/share/icons/hicolor/scalable/apps/{fname}"
        if os.path.exists(sys_icon):
            return sys_icon
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        asset_icon = os.path.join(base_dir, "assets", fname)
        if os.path.exists(asset_icon):
            return asset_icon
        return "input-keyboard"

