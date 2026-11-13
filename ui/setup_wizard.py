#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey Setup Wizard
Author: Victor Pham
"""

import sys
import os
import subprocess
import threading
import time
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

_INSTALLED = os.path.abspath(__file__).startswith("/usr/share/lotuskey")
_ENGINE_BIN   = "/usr/lib/lotuskey/ibus-engine-lotuskey" if _INSTALLED else os.path.join(BASE_DIR, "bin", "ibus-engine-lotuskey")
_ENGINE_LIB   = "/usr/lib/lotuskey" if _INSTALLED else os.path.join(BASE_DIR, "lib")
_ENGINE_INC   = os.path.join(BASE_DIR, "include")
_ENGINE_SRC   = os.path.join(BASE_DIR, "src", "main.c")
_SETUP_BIN    = "/usr/bin/lotuskey-setup" if _INSTALLED else os.path.join(BASE_DIR, "bin", "lotuskey-setup")
_MENU_BIN     = "/usr/bin/lotuskey-menu"  if _INSTALLED else os.path.join(BASE_DIR, "bin", "lotuskey-menu")
_COMP_XML_SRC = "/usr/share/ibus/component/lotuskey.xml" if _INSTALLED else os.path.join(BASE_DIR, "engine", "lotus.xml")

from config.config_manager import load_config, save_config, load_macros, set_autostart
from config.distro_adapter import DistroAdapter
from config.im_framework import (
    detect_installed_frameworks,
    resolve_effective_framework,
    generate_ibus_component_xml,
    apply_framework_config,
)
from config.i18n import tr, normalize_lang

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
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


def scan_system_environment(lang: str = "vi"):
    """Scans system environment, tools, and prerequisites across Linux distros."""
    results = []
    distro = DistroAdapter.detect_distro()

    results.append({
        "id": "distro",
        "name": tr(lang, "scan_distro"),
        "value": f"{distro['name']} ({distro['arch']})",
        "ok": True,
        "detail": f"{distro['family'].upper()} | {distro['pkg_manager']}"
    })

    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown").capitalize()
    is_wayland = "wayland" in session_type.lower()
    results.append({
        "id": "session",
        "name": tr(lang, "scan_session"),
        "value": f"{session_type} ({'Wayland' if is_wayland else 'X11'})",
        "ok": True,
        "detail": "GNOME, KDE Plasma, Hyprland, Sway, Cinnamon, XFCE"
    })

    fws = detect_installed_frameworks()
    active_fw = resolve_effective_framework("auto").upper()
    installed_names = [k.upper() for k, v in fws.items() if v.get("installed")]
    results.append({
        "id": "im_frameworks",
        "name": tr(lang, "scan_im"),
        "value": f"{', '.join(installed_names) or 'UInput'} ({active_fw})",
        "ok": len(installed_names) > 0,
        "detail": "IBus, Fcitx5, Fcitx4, Evdev/UInput"
    })

    gcc_path = shutil.which("gcc") or shutil.which("clang")
    gcc_ok = gcc_path is not None
    results.append({
        "id": "gcc",
        "name": tr(lang, "scan_gcc"),
        "value": tr(lang, "scan_installed") if gcc_ok else tr(lang, "scan_missing"),
        "ok": gcc_ok,
        "detail": gcc_path if gcc_ok else DistroAdapter.get_install_hint("build")
    })

    so_path = os.path.join(_ENGINE_LIB, "libLotusKeyCAPI.so")
    abi_ok, abi_reason = DistroAdapter.check_capi_library_compatible(so_path)
    results.append({
        "id": "lotuskey_core",
        "name": f"{tr(lang, 'scan_core')} ({distro['arch']})",
        "value": tr(lang, "scan_abi_ok") if abi_ok else abi_reason,
        "ok": abi_ok,
        "detail": f"{os.path.getsize(so_path):,} bytes" if abi_ok else abi_reason
    })

    results.append({
        "id": "gtk",
        "name": tr(lang, "scan_gtk"),
        "value": f"{tr(lang, 'scan_ready')} (GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()})",
        "ok": True,
        "detail": f"GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()}"
    })

    return results


def run_installation_step(step_idx, emit_log):
    """Executes a single installation step and returns True on success."""
    try:
        if step_idx == 1:
            emit_log("Initializing ~/.config/LotusKey and SVG icons...")
            DistroAdapter.install_user_icons(BASE_DIR)
            cfg = load_config()
            cfg["autostart"] = True
            save_config(cfg)
            emit_log("[OK] Configuration directory and icons initialized.")
            return True

        elif step_idx == 2:
            if _INSTALLED:
                emit_log("Verifying pre-installed engine binary...")
                if os.path.isfile(_ENGINE_BIN) and os.access(_ENGINE_BIN, os.X_OK):
                    emit_log(f"[OK] Engine binary verified: {_ENGINE_BIN}")
                    return True
                emit_log(f"[ERR] Missing engine binary: {_ENGINE_BIN}")
                return False
            else:
                emit_log("Checking libLotusKeyCAPI.so ABI compatibility...")
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

                emit_log("Compiling IBus engine (ibus-engine-lotuskey)...")
                cflags, ldflags = DistroAdapter.get_ibus_build_flags(BASE_DIR)
                cmd = [
                    cc_bin, "-O2", "-s", "-fno-ident",
                    "-Wl,--build-id=none", "-Wl,-z,relro,-z,now",
                    *cflags,
                    src_file,
                    "-Wl,-rpath,$ORIGIN",
                    "-Wl,-rpath,$ORIGIN/../lib",
                    "-Wl,-rpath,/usr/lib/lotuskey",
                    *ldflags,
                    "-o", out_bin
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    if os.path.isfile(out_bin) and os.access(out_bin, os.X_OK):
                        emit_log(f"[WARN] Using prebuilt binary: {out_bin}")
                    else:
                        emit_log(f"[WARN] IBus engine build skipped ({res.stderr.strip()}); continuing with UInput/Fcitx5.")

                uinput_src = os.path.join(BASE_DIR, "src", "uinput_daemon.c")
                uinput_bin = os.path.join(BASE_DIR, "bin", "lotuskey-uinput")
                if os.path.isfile(uinput_src):
                    cmd_uinput = [
                        cc_bin, "-O2", "-s", "-fno-ident",
                        "-Wl,--build-id=none", "-Wl,-z,relro,-z,now",
                        f"-I{inc_dir}", uinput_src,
                        f"-L{lib_dir}",
                        "-Wl,-rpath,$ORIGIN",
                        "-Wl,-rpath,$ORIGIN/../lib",
                        "-Wl,-rpath,/usr/lib/lotuskey",
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

                emit_log("[OK] Native binaries ready.")
                return True

        elif step_idx == 3:
            emit_log("Registering IBus Component XML and framework configuration...")
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

            if HAS_IBUS_GI and IBus is not None:
                try:
                    reg = IBus.Registry.new()
                    reg.load()
                    reg.load_in_dir(comp_dir)
                    cache_path = os.path.expanduser("~/.cache/ibus/bus/registry")
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    reg.save_cache_file(cache_path)
                except Exception as cache_err:
                    emit_log(f"[WARN] Skipped IBus registry cache: {cache_err}")
            emit_log("[OK] IBus component descriptor updated.")
            return True

        elif step_idx == 4:
            emit_log("Creating desktop entry and CLI symlinks...")
            if _INSTALLED:
                subprocess.run(
                    ["update-desktop-database", "-q", "/usr/share/applications/"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                emit_log("[OK] Desktop shortcuts verified.")
                return True
            else:
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
                    "Name=LotusKey Settings\n"
                    "Name[vi]=LotusKey - Cài đặt\n"
                    "Comment=Vietnamese Input Method for Linux\n"
                    "Comment[vi]=Bộ gõ tiếng Việt cho Linux\n"
                    f"Exec={setup_src}\n"
                    f"Icon={icon_path}\n"
                    "Terminal=false\n"
                    "Type=Application\n"
                    "Categories=Settings;Utility;\n"
                    "Keywords=lotus;lotuskey;vietnamese;telex;vni;ibus;fcitx5;\n"
                )
                with open(desktop_file, "w", encoding="utf-8") as f:
                    f.write(content)
                emit_log("[OK] Desktop entry and CLI commands created.")
                return True

        elif step_idx == 5:
            emit_log("Configuring OS autostart...")
            set_autostart(True)
            emit_log("[OK] Autostart entry written to ~/.config/autostart/lotuskey.desktop.")
            return True

        elif step_idx == 6:
            emit_log("Synchronizing input method framework and activating engine...")
            cfg = load_config()
            macros = load_macros()
            eff = apply_framework_config(cfg, macros, switch_daemon=False)
            if eff == "ibus" and shutil.which("ibus"):
                subprocess.run(["ibus", "restart"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1.0)
                subprocess.run(["ibus", "engine", "lotuskey"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            emit_log(f"[OK] LotusKey activated (Backend: {eff.upper()}).")
            return True

    except Exception as e:
        emit_log(f"[ERR] {e}")
        return False
    return False


def run_silent_setup():
    """Runs silent setup without GUI."""
    cfg = load_config()
    lang = normalize_lang(cfg.get("ui_lang", "vi"))
    print("=" * 64)
    print(f"{tr(lang, 'wiz_title')} (Silent Mode)")
    print(tr(lang, "wiz_author"))
    print("=" * 64)

    steps = [
        (1, tr(lang, "wiz_s1")),
        (2, tr(lang, "wiz_s2")),
        (3, tr(lang, "wiz_s3")),
        (4, tr(lang, "wiz_s4")),
        (5, tr(lang, "wiz_s5")),
        (6, tr(lang, "wiz_s6")),
    ]

    def log(msg):
        print(f"  {msg}")

    all_ok = True
    for idx, name in steps:
        print(f"\n[{idx}/6] {name}...")
        ok = run_installation_step(idx, log)
        if not ok:
            print(f"  [FAIL] {name}")
            all_ok = False
            break
        print(f"  [DONE] {name}")

    if all_ok:
        print("\n" + "=" * 64)
        print(tr(lang, "wiz_finish_head"))
        print("=" * 64)
        subprocess.Popen([_SETUP_BIN])
        return 0
    return 1


class SetupWizard(Gtk.Window):
    def __init__(self):
        self.cfg = load_config()
        self.lang = normalize_lang(self.cfg.get("ui_lang", "vi"))
        super().__init__(title=tr(self.lang, "wiz_title"))
        self.set_default_size(680, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self._updating_ui = False
        self.current_page = 0

        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_DATA)
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.get_style_context().add_class("wizard-window")

        self.root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.root_box)
        self._build_wizard_layout()

    def _t(self, key: str) -> str:
        return tr(self.lang, key)

    def _build_wizard_layout(self):
        for child in self.root_box.get_children():
            self.root_box.remove(child)

        self.set_title(self._t("wiz_title"))

        main_h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.root_box.pack_start(main_h_box, True, True, 0)

        # Left Sidebar
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.sidebar_box.set_size_request(200, -1)
        self.sidebar_box.get_style_context().add_class("sidebar-box")
        main_h_box.pack_start(self.sidebar_box, False, False, 0)

        lbl_logo = Gtk.Label(label="LotusKey", xalign=0)
        lbl_logo.get_style_context().add_class("wizard-title")
        self.sidebar_box.pack_start(lbl_logo, False, False, 0)

        lbl_author = Gtk.Label(label=self._t("wiz_author"), xalign=0)
        lbl_author.get_style_context().add_class("wizard-author")
        self.sidebar_box.pack_start(lbl_author, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(12)
        sep.set_margin_bottom(12)
        self.sidebar_box.pack_start(sep, False, False, 0)

        self.step_labels = []
        step_names = [
            self._t("wiz_step_1"),
            self._t("wiz_step_2"),
            self._t("wiz_step_3"),
            self._t("wiz_step_4"),
        ]
        for sname in step_names:
            lbl = Gtk.Label(label=sname, xalign=0)
            lbl.get_style_context().add_class("step-label")
            self.step_labels.append(lbl)
            self.sidebar_box.pack_start(lbl, False, False, 0)

        self.sidebar_box.pack_start(Gtk.Box(), True, True, 0)

        # Language selector at bottom of sidebar
        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_lang = Gtk.Label(label=self._t("lang_label"), xalign=0)
        lbl_lang.set_markup(f"<small>{self._t('lang_label')}</small>")
        self.cmb_lang = Gtk.ComboBoxText()
        self.cmb_lang.append("vi", "Tiếng Việt")
        self.cmb_lang.append("en", "English")
        self.cmb_lang.set_active_id(self.lang)
        self.cmb_lang.connect("changed", self._on_lang_changed)
        lang_box.pack_start(lbl_lang, False, False, 0)
        lang_box.pack_end(self.cmb_lang, True, True, 0)
        self.sidebar_box.pack_end(lang_box, False, False, 0)

        # Right Content Area (Stack)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        main_h_box.pack_start(self.stack, True, True, 0)

        self._build_welcome_page()
        self._build_scan_page()
        self._build_install_page()
        self._build_finish_page()

        # Bottom Action Bar
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_box.get_style_context().add_class("bottom-action-bar")
        bottom_box.set_halign(Gtk.Align.END)

        self.btn_cancel = Gtk.Button(label=self._t("wiz_btn_cancel"))
        self.btn_cancel.connect("clicked", lambda w: self.close())

        self.btn_back = Gtk.Button(label=self._t("wiz_btn_back"))
        self.btn_back.connect("clicked", self._on_back_clicked)
        self.btn_back.set_sensitive(False)

        self.btn_next = Gtk.Button(label=self._t("wiz_btn_next"))
        self.btn_next.get_style_context().add_class("suggested-action")
        self.btn_next.connect("clicked", self._on_next_clicked)

        bottom_box.pack_start(self.btn_cancel, False, False, 0)
        bottom_box.pack_start(self.btn_back, False, False, 0)
        bottom_box.pack_start(self.btn_next, False, False, 0)

        self.root_box.pack_end(bottom_box, False, False, 0)
        self.root_box.show_all()
        self._update_ui_state()

    def _on_lang_changed(self, combo):
        if self._updating_ui or self.current_page == 2:
            return
        new_lang = normalize_lang(combo.get_active_id())
        if new_lang != self.lang:
            self.lang = new_lang
            self.cfg["ui_lang"] = new_lang
            save_config(self.cfg)
            GLib.idle_add(self._build_wizard_layout)

    def _build_welcome_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.get_style_context().add_class("content-box")

        lbl_head = Gtk.Label(label=self._t("wiz_welcome_head"), xalign=0)
        lbl_head.get_style_context().add_class("page-heading")
        page.pack_start(lbl_head, False, False, 0)

        lbl_desc = Gtk.Label(label=self._t("wiz_welcome_desc"), xalign=0)
        lbl_desc.get_style_context().add_class("page-desc")
        page.pack_start(lbl_desc, False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("card-frame")

        lbl_info = Gtk.Label(label=self._t("wiz_welcome_body"), use_markup=True, xalign=0)
        lbl_info.set_line_wrap(True)
        card.pack_start(lbl_info, False, False, 0)
        page.pack_start(card, False, False, 0)

        self.chk_autostart_welcome = Gtk.CheckButton(label=self._t("wiz_chk_autostart"))
        self.chk_autostart_welcome.set_active(True)
        page.pack_start(self.chk_autostart_welcome, False, False, 4)

        self.chk_open_config_welcome = Gtk.CheckButton(label=self._t("wiz_chk_open_cfg"))
        self.chk_open_config_welcome.set_active(True)
        page.pack_start(self.chk_open_config_welcome, False, False, 4)

        self.stack.add_named(page, "page_welcome")

    def _build_scan_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.get_style_context().add_class("content-box")

        lbl_head = Gtk.Label(label=self._t("wiz_scan_head"), xalign=0)
        lbl_head.get_style_context().add_class("page-heading")
        page.pack_start(lbl_head, False, False, 0)

        lbl_desc = Gtk.Label(label=self._t("wiz_scan_desc"), xalign=0)
        lbl_desc.get_style_context().add_class("page-desc")
        page.pack_start(lbl_desc, False, False, 0)

        self.scan_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.scan_container.get_style_context().add_class("card-frame")
        page.pack_start(self.scan_container, True, True, 0)

        btn_rescan = Gtk.Button(label=self._t("wiz_btn_rescan"))
        btn_rescan.set_halign(Gtk.Align.START)
        btn_rescan.connect("clicked", lambda w: self._refresh_scan_results())
        page.pack_start(btn_rescan, False, False, 0)

        self.stack.add_named(page, "page_scan")

    def _refresh_scan_results(self):
        for child in self.scan_container.get_children():
            self.scan_container.remove(child)

        results = scan_system_environment(self.lang)
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

        lbl_head = Gtk.Label(label=self._t("wiz_inst_head"), xalign=0)
        lbl_head.get_style_context().add_class("page-heading")
        page.pack_start(lbl_head, False, False, 0)

        self.lbl_install_status = Gtk.Label(label=self._t("wiz_inst_prep"), xalign=0)
        self.lbl_install_status.get_style_context().add_class("page-desc")
        page.pack_start(self.lbl_install_status, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_show_text(True)
        page.pack_start(self.progress_bar, False, False, 8)

        self.install_step_labels = []
        step_names = [
            f"1. {self._t('wiz_s1')}",
            f"2. {self._t('wiz_s2')}",
            f"3. {self._t('wiz_s3')}",
            f"4. {self._t('wiz_s4')}",
            f"5. {self._t('wiz_s5')}",
            f"6. {self._t('wiz_s6')}",
        ]
        step_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        step_box.get_style_context().add_class("card-frame")
        for s in step_names:
            lbl = Gtk.Label(label=f"• {s}", xalign=0)
            self.install_step_labels.append(lbl)
            step_box.pack_start(lbl, False, False, 1)
        page.pack_start(step_box, False, False, 0)

        expander = Gtk.Expander(label=self._t("wiz_inst_log"))
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

        lbl_head = Gtk.Label(label=self._t("wiz_finish_head"), xalign=0)
        lbl_head.get_style_context().add_class("page-heading")
        page.pack_start(lbl_head, False, False, 0)

        lbl_desc = Gtk.Label(label=self._t("wiz_finish_desc"), xalign=0)
        lbl_desc.get_style_context().add_class("page-desc")
        page.pack_start(lbl_desc, False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("card-frame")

        lbl_sum = Gtk.Label(label=self._t("wiz_finish_body"), use_markup=True, xalign=0)
        card.pack_start(lbl_sum, False, False, 0)
        page.pack_start(card, False, False, 0)

        self.chk_open_config_finish = Gtk.CheckButton(label=self._t("wiz_chk_open_now"))
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
            self.btn_next.set_label(self._t("wiz_btn_next"))
            self.btn_next.set_sensitive(True)
        elif self.current_page == 1:
            self.btn_back.set_sensitive(True)
            self.btn_next.set_label(self._t("wiz_btn_install"))
            self.btn_next.set_sensitive(True)
            self._refresh_scan_results()
        elif self.current_page == 2:
            self.btn_back.set_sensitive(False)
            self.btn_cancel.set_sensitive(False)
            self.btn_next.set_sensitive(False)
            self.btn_next.set_label(self._t("wiz_btn_installing"))
            threading.Thread(target=self._run_installation_thread, daemon=True).start()
        elif self.current_page == 3:
            self.btn_back.set_sensitive(False)
            self.btn_cancel.set_visible(False)
            self.btn_next.set_sensitive(True)
            self.btn_next.set_label(self._t("wiz_btn_finish"))

    def _on_next_clicked(self, widget):
        if self.current_page == 3:
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
            (1, self._t("wiz_s1")),
            (2, self._t("wiz_s2")),
            (3, self._t("wiz_s3")),
            (4, self._t("wiz_s4")),
            (5, self._t("wiz_s5")),
            (6, self._t("wiz_s6")),
        ]

        total_steps = len(steps)
        for idx, name in steps:
            def _update_status(s_name=name, i=idx):
                self.lbl_install_status.set_text(f"({i}/{total_steps}) {s_name}...")
                self.progress_bar.set_fraction((i - 1) / total_steps)
            GLib.idle_add(_update_status)

            ok = run_installation_step(idx, self._append_log)
            time.sleep(0.25)

            def _mark_done(i=idx, success=ok):
                sym = "✔" if success else "✖"
                raw = self.install_step_labels[i - 1].get_text()[2:]
                self.install_step_labels[i - 1].set_text(f"{sym} {raw}")
                self.progress_bar.set_fraction(i / total_steps)
            GLib.idle_add(_mark_done)

        def _finish():
            self.current_page = 3
            self._update_ui_state()
        GLib.idle_add(_finish)


if __name__ == "__main__":
    if "--silent" in sys.argv or "--auto" in sys.argv:
        sys.exit(run_silent_setup())
    win = SetupWizard()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
