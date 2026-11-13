#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Windows-Style Setup Wizard
Author: Victor Pham
High-performance Vietnamese Input Method Engine for GNOME Wayland
"""

import sys
import os
import subprocess
import threading
import time
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Detect install mode: deb package installs to /usr/share/lotuskey
# Dev mode runs from project source directory
_INSTALLED = os.path.abspath(__file__).startswith("/usr/share/lotuskey")
_ENGINE_BIN   = "/usr/lib/lotuskey/ibus-engine-lotuskey" if _INSTALLED else os.path.join(BASE_DIR, "bin", "ibus-engine-lotuskey")
_ENGINE_LIB   = "/usr/lib/lotuskey" if _INSTALLED else os.path.join(BASE_DIR, "lib")
_ENGINE_INC   = os.path.join(BASE_DIR, "include")  # only needed in dev mode
_ENGINE_SRC   = os.path.join(BASE_DIR, "src", "main.c")
_SETUP_BIN    = "/usr/bin/lotuskey-setup" if _INSTALLED else os.path.join(BASE_DIR, "bin", "lotuskey-setup")
_MENU_BIN     = "/usr/bin/lotuskey-menu"  if _INSTALLED else os.path.join(BASE_DIR, "bin", "lotuskey-menu")
_COMP_XML_SRC = "/usr/share/ibus/component/lotuskey.xml" if _INSTALLED else os.path.join(BASE_DIR, "engine", "lotus.xml")

from config.config_manager import load_config, save_config, load_macros, set_autostart, is_autostart_enabled
from config.distro_adapter import DistroAdapter
from config.im_framework import (
    detect_installed_frameworks,
    resolve_effective_framework,
    generate_ibus_component_xml,
    apply_framework_config,
)

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango
try:
    gi.require_version('IBus', '1.0')
    from gi.repository import IBus
    HAS_IBUS_GI = True
except Exception:
    IBus = None
    HAS_IBUS_GI = False

CSS_DATA = b"""
window.wizard-window {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

.sidebar-box {
    background-color: #181825;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    padding: 24px 16px;
}

.wizard-title {
    font-size: 18px;
    font-weight: 800;
    color: #cdd6f4;
}

.wizard-author {
    font-size: 11px;
    font-weight: 600;
    color: #89b4fa;
    margin-top: 2px;
}

.step-label {
    font-size: 13px;
    font-weight: 500;
    color: #6c7086;
    padding: 6px 12px;
    border-radius: 6px;
}

.step-label.active {
    background-color: rgba(137, 180, 250, 0.15);
    color: #89b4fa;
    font-weight: 700;
}

.step-label.completed {
    color: #a6e3a1;
}

.content-box {
    padding: 24px 28px;
}

.page-heading {
    font-size: 16px;
    font-weight: 700;
    color: #cdd6f4;
    margin-bottom: 4px;
}

.page-desc {
    font-size: 12px;
    color: #a6adc8;
    margin-bottom: 16px;
}

.card-frame {
    background-color: #181825;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 12px;
}

.status-ok {
    color: #a6e3a1;
    font-weight: 600;
}

.status-warn {
    color: #f9e2af;
    font-weight: 600;
}

.status-err {
    color: #f38ba8;
    font-weight: 600;
}

.log-view {
    font-family: monospace;
    font-size: 11px;
    background-color: #11111b;
    color: #a6adc8;
    padding: 8px;
    border-radius: 6px;
}

.bottom-action-bar {
    background-color: #181825;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding: 12px 20px;
}
"""

def scan_system_environment():
    """Scans system environment, tools, and prerequisites across any Linux distro."""
    results = []
    distro = DistroAdapter.detect_distro()

    # 0. Linux Distribution & Architecture
    results.append({
        "id": "distro",
        "name": "Bản phân phối Linux (OS & Kiến trúc)",
        "value": f"{distro['name']} ({distro['arch']})",
        "ok": True,
        "detail": f"Họ distro: {str(distro['family']).upper()} | Trình quản lý gói: {distro['pkg_manager']}"
    })

    # 1. Desktop Session & Display
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown").capitalize()
    is_wayland = "wayland" in session_type.lower()
    results.append({
        "id": "session",
        "name": "Môi trường hiển thị (Display Session)",
        "value": f"{session_type} ({'Wayland Native' if is_wayland else 'X11'})",
        "ok": True,
        "detail": "Tương thích với GNOME, KDE Plasma, Hyprland, Sway, Cinnamon, XFCE."
    })

    # 2. Multi-Framework Input Method Engines (IBus / Fcitx5 / UInput)
    fws = detect_installed_frameworks()
    active_fw = resolve_effective_framework("auto").upper()
    installed_names = [k.upper() for k, v in fws.items() if v.get("installed")]
    results.append({
        "id": "im_frameworks",
        "name": "Hệ thống Bộ gõ Linux (Multi-Backend)",
        "value": f"Đã cài: {', '.join(installed_names) or 'UInput'} (Tối ưu: {active_fw})",
        "ok": len(installed_names) > 0,
        "detail": "Hỗ trợ đồng thời IBus, Fcitx5, Fcitx4 và Evdev/UInput."
    })

    # 3. C/C++ Compiler Toolchain
    gcc_path = shutil.which("gcc") or shutil.which("clang")
    gcc_ok = (gcc_path is not None)
    results.append({
        "id": "gcc",
        "name": "Trình biên dịch C/C++ (GCC / Clang)",
        "value": "Đã cài đặt" if gcc_ok else "Chưa cài đặt",
        "ok": gcc_ok,
        "detail": f"Đường dẫn: {gcc_path}" if gcc_ok else f"Gợi ý cài: {DistroAdapter.get_install_hint('build')}"
    })

    # 4. Native LotusKey Core Library (ABI check + Fallback Source support)
    so_path = os.path.join(_ENGINE_LIB, "libLotusKeyCAPI.so")
    abi_ok, abi_reason = DistroAdapter.check_capi_library_compatible(so_path)
    has_fallback_src = os.path.exists(os.path.join(BASE_DIR, "src", "lotuskey_capi_fallback.cpp"))
    so_ok = abi_ok or (has_fallback_src and shutil.which("g++") is not None)
    results.append({
        "id": "lotuskey_core",
        "name": f"Thư viện xử lý tiếng Việt ({distro['arch']})",
        "value": "Tương thích ABI" if abi_ok else ("Sẵn sàng biên dịch từ nguồn C++" if so_ok else "Không tương thích"),
        "ok": so_ok,
        "detail": f"Kích thước: {os.path.getsize(so_path):,} bytes" if abi_ok else f"Tự động build native cho {distro['arch']} ({abi_reason})"
    })

    # 5. GTK & Python GObject
    results.append({
        "id": "gtk",
        "name": "Giao diện GTK & Python GObject",
        "value": "Đã sẵn sàng",
        "ok": True,
        "detail": f"Phiên bản GTK: {Gtk.get_major_version()}.{Gtk.get_minor_version()}"
    })

    return results

def run_installation_step(step_idx, emit_log):
    """Executes a single installation step and returns True on success."""
    try:
        if step_idx == 1:
            emit_log("Khởi tạo thư mục cấu hình LotusKey (~/.config/LotusKey) & bộ Icon SVG...")
            DistroAdapter.install_user_icons(BASE_DIR)
            cfg = load_config()
            cfg["autostart"] = True
            save_config(cfg)
            emit_log("✓ Cấu hình ban đầu và Icon hệ thống đã sẵn sàng.")
            return True

        elif step_idx == 2:
            if _INSTALLED:
                # Package mode: engine đã được cài bởi package manager, chỉ verify
                emit_log("Kiểm tra Native C IBus Engine (đã cài từ package)...")
                if os.path.isfile(_ENGINE_BIN) and os.access(_ENGINE_BIN, os.X_OK):
                    emit_log(f"✓ Engine sẵn sàng: {_ENGINE_BIN}")
                    return True
                else:
                    emit_log(f"✖ Không tìm thấy engine tại: {_ENGINE_BIN}")
                    return False
            else:
                # Dev / Universal Source mode: verify CAPI ABI first, then compile C engines
                emit_log("Kiểm tra tương thích ABI của libLotusKeyCAPI.so...")
                capi_ok, capi_msg = DistroAdapter.ensure_capi_library(BASE_DIR)
                emit_log(f" -> {capi_msg}")
                if not capi_ok:
                    return False

                src_file = _ENGINE_SRC
                out_bin  = _ENGINE_BIN
                lib_dir  = _ENGINE_LIB
                inc_dir  = _ENGINE_INC
                cc_bin   = shutil.which("gcc") or shutil.which("clang") or "cc"

                so0_link = os.path.join(lib_dir, "libLotusKeyCAPI.so.0")
                if not os.path.exists(so0_link):
                    try:
                        os.symlink("libLotusKeyCAPI.so", so0_link)
                    except Exception:
                        pass

                emit_log("Biên dịch Native C IBus Engine (ibus-engine-lotuskey)...")
                cflags, ldflags = DistroAdapter.get_ibus_build_flags(BASE_DIR)
                cmd = [
                    cc_bin, "-O2",
                    *cflags,
                    src_file,
                    "-Wl,-rpath,$ORIGIN",
                    "-Wl,-rpath,$ORIGIN/../lib",
                    "-Wl,-rpath,/usr/lib/lotuskey",
                    *ldflags,
                    "-o", out_bin
                ]
                emit_log(f"Chạy lệnh: {' '.join(cmd)}")
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    if os.path.isfile(out_bin) and os.access(out_bin, os.X_OK):
                        emit_log(f"⚠ Bỏ qua biên dịch lại, dùng binary có sẵn: {out_bin}")
                    else:
                        emit_log(f"⚠ Không thể biên dịch IBus engine ({res.stderr.strip()}), tiếp tục với UInput/Fcitx5.")

                # Also compile lotuskey-uinput universal daemon
                uinput_src = os.path.join(BASE_DIR, "src", "uinput_daemon.c")
                uinput_bin = os.path.join(BASE_DIR, "bin", "lotuskey-uinput")
                if os.path.isfile(uinput_src):
                    cmd_uinput = [
                        cc_bin, "-O2", f"-I{inc_dir}", uinput_src,
                        f"-L{lib_dir}", "-Wl,-rpath,$ORIGIN", "-Wl,-rpath,$ORIGIN/../lib",
                        f"-Wl,-rpath,{lib_dir}", "-Wl,-rpath,/usr/lib/lotuskey",
                        "-lLotusKeyCAPI", "-o", uinput_bin
                    ]
                    subprocess.run(cmd_uinput, capture_output=True, text=True, check=False)
                    if os.path.isfile(uinput_bin):
                        os.chmod(uinput_bin, 0o755)

                if os.path.isfile(out_bin):
                    legacy_bin = os.path.join(BASE_DIR, "bin", "ibus-engine-lotus")
                    if os.path.exists(legacy_bin) or os.path.islink(legacy_bin):
                        os.remove(legacy_bin)
                    os.symlink("ibus-engine-lotuskey", legacy_bin)
                    os.chmod(out_bin, 0o755)

                emit_log("✓ Biên dịch Native Engines (IBus & UInput) thành công.")
                return True

        elif step_idx == 3:
            emit_log("Cài đặt IBus Component XML, Fcitx5 Adapter & Registry Cache...")
            comp_dir = os.path.expanduser("~/.local/share/ibus/component")
            os.makedirs(comp_dir, exist_ok=True)
            dup_xml = os.path.join(comp_dir, "lotus.xml")
            if os.path.exists(dup_xml):
                try:
                    os.remove(dup_xml)
                except Exception:
                    pass
            xml_content = generate_ibus_component_xml(_ENGINE_BIN, _SETUP_BIN)
            with open(os.path.join(comp_dir, "lotuskey.xml"), "w", encoding="utf-8") as f:
                f.write(xml_content)

            # Build IBus Registry Cache (if gir1.2-ibus-1.0 is available)
            if HAS_IBUS_GI and IBus is not None:
                try:
                    reg = IBus.Registry.new()
                    reg.load()
                    reg.load_in_dir(comp_dir)
                    cache_path = os.path.expanduser("~/.cache/ibus/bus/registry")
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    reg.save_cache_file(cache_path)
                except Exception as cache_err:
                    emit_log(f"⚠ Bỏ qua tạo IBus cache: {cache_err}")
            emit_log("✓ Đã cập nhật IBus Component Descriptor & Multi-Framework Config.")
            return True

        elif step_idx == 4:
            emit_log("Tạo Desktop Shortcut & liên kết lệnh CLI...")
            if _INSTALLED:
                # Deb mode: bins đã ở /usr/bin/, desktop files ở /usr/share/applications/
                # Chỉ cần đảm bảo xdg database được update
                subprocess.run(["update-desktop-database", "-q", "/usr/share/applications/"],
                               check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                emit_log("✓ Desktop shortcuts đã sẵn sàng (cài từ package).")
                return True
            else:
                # Dev mode: tạo symlinks vào ~/.local/bin
                local_bin = os.path.expanduser("~/.local/bin")
                os.makedirs(local_bin, exist_ok=True)
                setup_src = _SETUP_BIN
                menu_src  = _MENU_BIN

                for src in (setup_src, menu_src):
                    if os.path.exists(src):
                        os.chmod(src, 0o755)

                for target, link_name in [
                    (setup_src, os.path.join(local_bin, "lotuskey")),
                    (setup_src, os.path.join(local_bin, "lotuskey-setup")),
                    (menu_src,  os.path.join(local_bin, "lotuskey-menu")),
                ]:
                    if os.path.exists(link_name) or os.path.islink(link_name):
                        os.remove(link_name)
                    os.symlink(target, link_name)

                apps_dir = os.path.expanduser("~/.local/share/applications")
                os.makedirs(apps_dir, exist_ok=True)
                desktop_file = os.path.join(apps_dir, "lotuskey-setup.desktop")
                icon_path = DistroAdapter.get_icon_path(active=True)
                content = (
                    "[Desktop Entry]\n"
                    "Name=LotusKey - Bảng điều khiển\n"
                    "Comment=Bộ gõ tiếng Việt LotusKey Native Wayland (Tác giả: Victor Pham)\n"
                    f"Exec={setup_src}\n"
                    f"Icon={icon_path}\n"
                    "Terminal=false\n"
                    "Type=Application\n"
                    "Categories=Settings;Utility;\n"
                    "Keywords=lotus;lotuskey;vietnamese;telex;vni;ibus;fcitx5;\n"
                )
                with open(desktop_file, "w", encoding="utf-8") as f:
                    f.write(content)
                emit_log("✓ Đã tạo Desktop Shortcut và các lệnh CLI: lotuskey, lotuskey-setup, lotuskey-menu.")
                return True

        elif step_idx == 5:
            emit_log("Cấu hình Khởi động cùng hệ thống (Autostart with OS)...")
            set_autostart(True)
            emit_log("✓ Đã thiết lập tệp Autostart tại ~/.config/autostart/lotuskey.desktop.")
            return True

        elif step_idx == 6:
            emit_log("Đồng bộ Multi-Framework (IBus / Fcitx5 / UInput) & Kích hoạt bộ gõ...")
            cfg = load_config()
            macros = load_macros()
            eff = apply_framework_config(cfg, macros, switch_daemon=False)
            if eff == "ibus" and shutil.which("ibus"):
                subprocess.run(["ibus", "restart"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1.0)
                subprocess.run(["ibus", "engine", "lotuskey"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            emit_log(f"✓ Bộ gõ LotusKey đã được kích hoạt thành công (Backend: {eff.upper()})!")
            return True

    except Exception as e:
        emit_log(f"Lỗi: {e}")
        return False
    return False

def run_silent_setup():
    """Runs silent setup without GUI."""
    print("=" * 64)
    print("🌸 LotusKey Setup Wizard — Chế độ cài đặt tự động (Silent Mode)")
    print("Tác giả: Victor Pham")
    print("=" * 64)

    steps = [
        (1, "Quét và chuẩn bị thư mục cấu hình LotusKey"),
        (2, "Biên dịch Native C IBus Engine (ibus-engine-lotuskey)"),
        (3, "Đăng ký IBus Component Descriptor & Registry Cache"),
        (4, "Tạo Desktop Shortcut & liên kết lệnh CLI"),
        (5, "Thiết lập Khởi động cùng hệ thống (Autostart with OS)"),
        (6, "Tích hợp GNOME Input Sources & Kích hoạt bộ gõ")
    ]

    def log(msg):
        print(f"  [Log] {msg}")

    all_ok = True
    for idx, name in steps:
        print(f"\n[{idx}/6] {name}...")
        ok = run_installation_step(idx, log)
        if not ok:
            print(f"  ❌ Thất bại tại bước: {name}")
            all_ok = False
            break
        print(f"  ✔ Hoàn tất: {name}")

    if all_ok:
        print("\n" + "=" * 64)
        print("🎉 Cài đặt LotusKey thành công!")
        print("• Tác giả: Victor Pham")
        print("• Kiểu gõ mặc định: Telex (Chuyển sang VNI trong bảng điều khiển)")
        print("• Phím tắt chuyển Anh/Việt: Ctrl + Shift hoặc Alt + Z")
        print("• Menu nhanh Quick Menu: Phím ` (grave key)")
        print("=" * 64)
        print("\nKhởi chạy Bảng điều khiển cấu hình...")
        subprocess.Popen([_SETUP_BIN])
        return 0
    else:
        print("\n❌ Cài đặt thất bại. Vui lòng kiểm tra lại log bên trên.")
        return 1

class SetupWizard(Gtk.Window):
    def __init__(self):
        super().__init__(title="LotusKey Setup Wizard — Trình cài đặt")
        self.set_default_size(680, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)

        # Style context
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_DATA)
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.get_style_context().add_class("wizard-window")

        # Main Layout: Sidebar (Left) + Content (Right)
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root_box)

        main_h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        root_box.pack_start(main_h_box, True, True, 0)

        # Left Sidebar
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.sidebar_box.set_size_request(200, -1)
        self.sidebar_box.get_style_context().add_class("sidebar-box")
        main_h_box.pack_start(self.sidebar_box, False, False, 0)

        lbl_logo = Gtk.Label(label="🪷 LotusKey", xalign=0)
        lbl_logo.get_style_context().add_class("wizard-title")
        self.sidebar_box.pack_start(lbl_logo, False, False, 0)

        lbl_author = Gtk.Label(label="Tác giả: Victor Pham", xalign=0)
        lbl_author.get_style_context().add_class("wizard-author")
        self.sidebar_box.pack_start(lbl_author, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(12)
        sep.set_margin_bottom(12)
        self.sidebar_box.pack_start(sep, False, False, 0)

        self.step_labels = []
        step_names = [
            "1. Chào mừng",
            "2. Quét môi trường",
            "3. Tiến trình cài đặt",
            "4. Hoàn tất"
        ]
        for idx, sname in enumerate(step_names):
            lbl = Gtk.Label(label=sname, xalign=0)
            lbl.get_style_context().add_class("step-label")
            self.step_labels.append(lbl)
            self.sidebar_box.pack_start(lbl, False, False, 0)

        # Spacer in sidebar
        self.sidebar_box.pack_start(Gtk.Box(), True, True, 0)

        # Right Content Area (Stack)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        main_h_box.pack_start(self.stack, True, True, 0)

        # Build Wizard Pages
        self._build_welcome_page()
        self._build_scan_page()
        self._build_install_page()
        self._build_finish_page()

        # Bottom Action Bar
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_box.get_style_context().add_class("bottom-action-bar")
        bottom_box.set_halign(Gtk.Align.END)

        self.btn_cancel = Gtk.Button(label="Hủy bỏ")
        self.btn_cancel.connect("clicked", lambda w: self.close())

        self.btn_back = Gtk.Button(label="< Quay lại")
        self.btn_back.connect("clicked", self._on_back_clicked)
        self.btn_back.set_sensitive(False)

        self.btn_next = Gtk.Button(label="Tiếp tục >")
        self.btn_next.get_style_context().add_class("suggested-action")
        self.btn_next.connect("clicked", self._on_next_clicked)

        bottom_box.pack_start(self.btn_cancel, False, False, 0)
        bottom_box.pack_start(self.btn_back, False, False, 0)
        bottom_box.pack_start(self.btn_next, False, False, 0)

        root_box.pack_end(bottom_box, False, False, 0)

        self.current_page = 0
        self._update_ui_state()

    def _build_welcome_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.get_style_context().add_class("content-box")

        lbl_head = Gtk.Label(label="Chào mừng bạn đến với trình cài đặt LotusKey", xalign=0)
        lbl_head.get_style_context().add_class("page-heading")
        page.pack_start(lbl_head, False, False, 0)

        lbl_desc = Gtk.Label(
            label="Trình cài đặt sẽ tự động thiết lập và tối ưu bộ gõ tiếng Việt Native Wayland cho Ubuntu/GNOME.",
            xalign=0
        )
        lbl_desc.get_style_context().add_class("page-desc")
        page.pack_start(lbl_desc, False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("card-frame")

        info_text = (
            "<b>🌸 LotusKey</b> — Bộ gõ tiếng Việt Native Wayland thế hệ mới "
            "với kiến trúc <b>Native IBus Engine</b>:\n\n"
            "• Triệt tiêu hoàn toàn lỗi nuốt chữ/mất ký tự trên Electron/VS Code/Chrome.\n"
            "• Hỗ trợ đầy đủ kiểu gõ Telex &amp; VNI, gõ tắt phụ âm, phím chuyển Unikey.\n"
            "• Menu nhanh Floating Quick Menu phím ` (grave key).\n"
            "• Tự động đăng ký và khởi động cùng hệ thống.\n\n"
            "<small>Tác giả: <b>Victor Pham</b> • Giấy phép mã nguồn mở MIT</small>"
        )
        lbl_info = Gtk.Label(label=info_text, use_markup=True, xalign=0)
        lbl_info.set_line_wrap(True)
        card.pack_start(lbl_info, False, False, 0)
        page.pack_start(card, False, False, 0)

        self.chk_autostart_welcome = Gtk.CheckButton(label="Khởi động LotusKey cùng hệ thống (Autostart with OS)")
        self.chk_autostart_welcome.set_active(True)
        page.pack_start(self.chk_autostart_welcome, False, False, 4)

        self.chk_open_config_welcome = Gtk.CheckButton(label="Mở Bảng điều khiển để tùy chỉnh cấu hình ngay sau khi cài đặt")
        self.chk_open_config_welcome.set_active(True)
        page.pack_start(self.chk_open_config_welcome, False, False, 4)

        self.stack.add_named(page, "page_welcome")

    def _build_scan_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.get_style_context().add_class("content-box")

        lbl_head = Gtk.Label(label="Quét môi trường & phụ thuộc hệ thống", xalign=0)
        lbl_head.get_style_context().add_class("page-heading")
        page.pack_start(lbl_head, False, False, 0)

        lbl_desc = Gtk.Label(
            label="Kiểm tra tính tương thích và sự sẵn sàng của các thành phần:",
            xalign=0
        )
        lbl_desc.get_style_context().add_class("page-desc")
        page.pack_start(lbl_desc, False, False, 0)

        self.scan_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.scan_container.get_style_context().add_class("card-frame")
        page.pack_start(self.scan_container, True, True, 0)

        btn_rescan = Gtk.Button(label="🔄 Quét lại")
        btn_rescan.set_halign(Gtk.Align.START)
        btn_rescan.connect("clicked", lambda w: self._refresh_scan_results())
        page.pack_start(btn_rescan, False, False, 0)

        self.stack.add_named(page, "page_scan")

    def _refresh_scan_results(self):
        for child in self.scan_container.get_children():
            self.scan_container.remove(child)

        results = scan_system_environment()
        for item in results:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            status_symbol = "✔" if item["ok"] else "✖"
            status_class = "status-ok" if item["ok"] else "status-err"
            lbl_sym = Gtk.Label(label=status_symbol)
            lbl_sym.get_style_context().add_class(status_class)
            row.pack_start(lbl_sym, False, False, 0)

            lbl_name = Gtk.Label(label=f"<b>{item['name']}</b>: {item['value']}", use_markup=True, xalign=0)
            row.pack_start(lbl_name, True, True, 0)

            self.scan_container.pack_start(row, False, False, 2)
        self.scan_container.show_all()

    def _build_install_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.get_style_context().add_class("content-box")

        lbl_head = Gtk.Label(label="Đang cài đặt LotusKey...", xalign=0)
        lbl_head.get_style_context().add_class("page-heading")
        page.pack_start(lbl_head, False, False, 0)

        self.lbl_install_status = Gtk.Label(label="Chuẩn bị cài đặt...", xalign=0)
        self.lbl_install_status.get_style_context().add_class("page-desc")
        page.pack_start(self.lbl_install_status, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_show_text(True)
        page.pack_start(self.progress_bar, False, False, 8)

        # Step check indicators
        self.install_step_labels = []
        step_names = [
            "1. Chuẩn bị thư mục cấu hình (~/.config/LotusKey)",
            "2. Biên dịch Native C IBus Engine (ibus-engine-lotuskey)",
            "3. Đăng ký IBus Component Descriptor & Registry Cache",
            "4. Tạo Desktop Application Shortcut & liên kết lệnh CLI",
            "5. Thiết lập Khởi động cùng hệ thống (Autostart with OS)",
            "6. Tích hợp GNOME Input Sources & Kích hoạt bộ gõ"
        ]
        step_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        step_box.get_style_context().add_class("card-frame")
        for s in step_names:
            lbl = Gtk.Label(label=f"⏳ {s}", xalign=0)
            self.install_step_labels.append(lbl)
            step_box.pack_start(lbl, False, False, 1)
        page.pack_start(step_box, False, False, 0)

        # Expander for live log
        expander = Gtk.Expander(label="Xem chi tiết tiến trình (Details Log)")
        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(-1, 80)
        self.log_text_view = Gtk.TextView()
        self.log_text_view.set_editable(False)
        self.log_text_view.set_cursor_visible(False)
        self.log_text_view.get_style_context().add_class("log-view")
        self.log_buffer = self.log_text_view.get_buffer()
        scroll.add(self.log_text_view)
        expander.add(scroll)
        page.pack_start(expander, True, True, 0)

        self.stack.add_named(page, "page_install")

    def _build_finish_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.get_style_context().add_class("content-box")

        lbl_head = Gtk.Label(label="🎉 Cài đặt LotusKey thành công!", xalign=0)
        lbl_head.get_style_context().add_class("page-heading")
        page.pack_start(lbl_head, False, False, 0)

        lbl_desc = Gtk.Label(
            label="Bộ gõ tiếng Việt LotusKey đã sẵn sàng hoạt động trên GNOME Wayland.",
            xalign=0
        )
        lbl_desc.get_style_context().add_class("page-desc")
        page.pack_start(lbl_desc, False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("card-frame")

        summary_text = (
            "<b>Thông tin cấu hình nhanh:</b>\n"
            "• Tác giả: <b>Victor Pham</b>\n"
            "• Kiểu gõ đang bật: <b>Telex</b> (hỗ trợ VNI chuyển đổi nhanh)\n"
            "• Phím chuyển Anh/Việt: <b>Ctrl + Shift</b> hoặc <b>Alt + Z</b>\n"
            "• Menu nhanh Floating Quick Menu: Bấm phím <b>`</b> (grave key)\n"
            "• Tự khởi động cùng OS: <b>Đã kích hoạt</b>\n\n"
            "Nhấn <b>Hoàn tất</b> để mở Bảng điều khiển và bắt đầu gõ tiếng Việt!"
        )
        lbl_sum = Gtk.Label(label=summary_text, use_markup=True, xalign=0)
        card.pack_start(lbl_sum, False, False, 0)
        page.pack_start(card, False, False, 0)

        self.chk_open_config_finish = Gtk.CheckButton(label="Mở Bảng điều khiển cấu hình ngay bây giờ")
        self.chk_open_config_finish.set_active(True)
        page.pack_start(self.chk_open_config_finish, False, False, 4)

        self.stack.add_named(page, "page_finish")

    def _append_log(self, text):
        def _do_append():
            end_iter = self.log_buffer.get_end_iter()
            self.log_buffer.insert(end_iter, text + "\n")
            self.log_text_view.scroll_to_iter(self.log_buffer.get_end_iter(), 0.0, False, 0.0, 0.0)
        GLib.idle_add(_do_append)

    def _update_ui_state(self):
        page_names = ["page_welcome", "page_scan", "page_install", "page_finish"]
        self.stack.set_visible_child_name(page_names[self.current_page])

        for idx, lbl in enumerate(self.step_labels):
            ctx = lbl.get_style_context()
            ctx.remove_class("active")
            ctx.remove_class("completed")
            if idx == self.current_page:
                ctx.add_class("active")
            elif idx < self.current_page:
                ctx.add_class("completed")

        if self.current_page == 0:
            self.btn_back.set_sensitive(False)
            self.btn_next.set_label("Tiếp tục >")
            self.btn_next.set_sensitive(True)
        elif self.current_page == 1:
            self.btn_back.set_sensitive(True)
            self.btn_next.set_label("Cài đặt >")
            self.btn_next.set_sensitive(True)
            self._refresh_scan_results()
        elif self.current_page == 2:
            self.btn_back.set_sensitive(False)
            self.btn_cancel.set_sensitive(False)
            self.btn_next.set_sensitive(False)
            self.btn_next.set_label("Đang cài đặt...")
            threading.Thread(target=self._run_installation_thread, daemon=True).start()
        elif self.current_page == 3:
            self.btn_back.set_sensitive(False)
            self.btn_cancel.set_visible(False)
            self.btn_next.set_sensitive(True)
            self.btn_next.set_label("Hoàn tất (Finish)")

    def _on_next_clicked(self, widget):
        if self.current_page == 3:
            # Finish clicked: open setup panel if checked
            if self.chk_open_config_finish.get_active():
                subprocess.Popen([_SETUP_BIN])
            self.close()
            return

        self.current_page += 1
        self._update_ui_state()

    def _on_back_clicked(self, widget):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_ui_state()

    def _run_installation_thread(self):
        steps = [
            (1, "Khởi tạo cấu hình LotusKey"),
            (2, "Biên dịch Native C IBus Engine"),
            (3, "Đăng ký IBus Component Descriptor"),
            (4, "Tạo Desktop Shortcut & CLI"),
            (5, "Cấu hình Autostart cùng hệ thống"),
            (6, "Kích hoạt GNOME Input Sources")
        ]

        total_steps = len(steps)
        for idx, name in steps:
            def _update_status(s_name=name, i=idx):
                self.lbl_install_status.set_text(f"Đang thực hiện ({i}/{total_steps}): {s_name}...")
                self.progress_bar.set_fraction((i - 1) / total_steps)
                self.install_step_labels[i - 1].set_text(f"⏳ {self.install_step_labels[i - 1].get_text()[2:]}")
            GLib.idle_add(_update_status)

            ok = run_installation_step(idx, self._append_log)
            time.sleep(0.3)

            def _mark_done(i=idx, success=ok):
                sym = "✔" if success else "✖"
                raw = self.install_step_labels[i - 1].get_text()[2:]
                self.install_step_labels[i - 1].set_text(f"{sym} {raw}")
                self.progress_bar.set_fraction(i / total_steps)
            GLib.idle_add(_mark_done)

            if not ok:
                def _mark_fail():
                    self.lbl_install_status.set_text("❌ Cài đặt gặp sự cố. Vui lòng xem log chi tiết.")
                GLib.idle_add(_mark_fail)
                return

        def _finish_all():
            self.lbl_install_status.set_text("✓ Hoàn tất tất cả các bước cài đặt!")
            self.progress_bar.set_fraction(1.0)
            time.sleep(0.5)
            self.current_page = 3
            self._update_ui_state()
        GLib.idle_add(_finish_all)

def main():
    if "--silent" in sys.argv or "-s" in sys.argv or "--quiet" in sys.argv or not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        sys.exit(run_silent_setup())

    win = SetupWizard()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.present()
    Gtk.main()

if __name__ == '__main__':
    main()
