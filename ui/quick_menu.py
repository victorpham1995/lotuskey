#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Quick Menu Dialog
Floating dialog triggered by pressing ` (grave) or via shortcut.
Features Flat Flag SVG preview, Icon Style quick switcher, Unified Theme (Auto/Dark/Light),
and 1-click access to Clipboard Converter and Full Settings.
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.config_manager import load_config, save_config
from config.distro_adapter import DistroAdapter
from config.i18n import normalize_lang, tr
from config.im_framework import apply_framework_config, resolve_effective_framework

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

CSS_DARK = b"""
window.quick-dialog {
    background-color: #1a1b26;
    color: #c0caf5;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 14px;
}
.lotus-title {
    font-size: 15px;
    font-weight: 700;
    color: #c0caf5;
    margin-bottom: 2px;
}
.lotus-subtitle {
    font-size: 11px;
    color: #7aa2f7;
    margin-bottom: 8px;
}
.section-label {
    font-size: 11px;
    font-weight: 600;
    color: #7dcfff;
    margin-top: 6px;
    margin-bottom: 4px;
}
button.mode-btn {
    background: #24283b;
    color: #a9b1d6;
    border: 1px solid #414868;
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 500;
}
button.mode-btn:hover {
    background: #2ac3de;
    color: #1a1b26;
}
button.mode-btn.active {
    background: #7aa2f7;
    color: #1a1b26;
    font-weight: 700;
    border-color: #7aa2f7;
}
combobox button {
    background: #24283b;
    background-image: none;
    color: #c0caf5;
    border: 1px solid #414868;
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 12px;
}
combobox button:hover {
    border-color: #7aa2f7;
}
button.lang-btn {
    background: #24283b;
    color: #c0caf5;
    border: 1px solid #414868;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
checkbutton {
    color: #c0caf5;
    font-size: 12px;
    margin-top: 2px;
    margin-bottom: 2px;
}
.hint-bar {
    font-size: 11px;
    color: #565f89;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 8px;
    margin-top: 6px;
}
"""

CSS_LIGHT = b"""
window.quick-dialog {
    background-color: #f8f9fc;
    color: #1e293b;
    border: 1px solid rgba(0, 0, 0, 0.16);
    border-radius: 14px;
}
.lotus-title {
    font-size: 15px;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 2px;
}
.lotus-subtitle {
    font-size: 11px;
    color: #d81b60;
    margin-bottom: 8px;
}
.section-label {
    font-size: 11px;
    font-weight: 600;
    color: #475569;
    margin-top: 6px;
    margin-bottom: 4px;
}
button.mode-btn {
    background: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 500;
}
button.mode-btn:hover {
    background: #e2e8f0;
    color: #0f172a;
}
button.mode-btn.active {
    background: #d81b60;
    color: #ffffff;
    font-weight: 700;
    border-color: #d81b60;
}
combobox button {
    background: #ffffff;
    background-image: none;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 12px;
}
combobox button:hover {
    border-color: #d81b60;
}
button.lang-btn {
    background: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
checkbutton {
    color: #1e293b;
    font-size: 12px;
    margin-top: 2px;
    margin-bottom: 2px;
}
.hint-bar {
    font-size: 11px;
    color: #64748b;
    border-top: 1px solid rgba(0, 0, 0, 0.08);
    padding-top: 8px;
    margin-top: 6px;
}
"""


class QuickMenuDialog(Gtk.Window):
    def __init__(self, on_config_changed=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_config_changed = on_config_changed
        self.cfg = load_config()
        self.lang = normalize_lang(self.cfg.get("ui_lang", "vi"))
        self._updating_ui = False

        self.set_title(tr(self.lang, "quick_menu_title"))
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)

        theme_mode = str(self.cfg.get("theme", "auto")).lower()
        settings = Gtk.Settings.get_default()
        if theme_mode == "dark":
            use_dark = True
            if settings:
                settings.set_property("gtk-application-prefer-dark-theme", True)
        elif theme_mode == "light":
            use_dark = False
            if settings:
                settings.set_property("gtk-application-prefer-dark-theme", False)
        else:
            prefer_dark = False
            if settings:
                prefer_dark = bool(settings.get_property("gtk-application-prefer-dark-theme"))
                tname = str(settings.get_property("gtk-theme-name") or "").lower()
                if "dark" in tname:
                    prefer_dark = True
            use_dark = prefer_dark

        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_DARK if use_dark else CSS_LIGHT)
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.get_style_context().add_class("quick-dialog")

        self.root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.root_box)
        self._build_content()

        self.connect("key-press-event", self._on_key_press)
        self.connect("focus-out-event", self._on_focus_out)

    def _build_content(self):
        for child in self.root_box.get_children():
            self.root_box.remove(child)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        self.root_box.pack_start(main_box, True, True, 0)

        eff_fw = resolve_effective_framework(self.cfg.get("im_framework", "auto")).upper()
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.hdr_icon = Gtk.Image()
        header_box.pack_start(self.hdr_icon, False, False, 0)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        lbl_title = Gtk.Label(label="LotusKey", xalign=0)
        lbl_title.get_style_context().add_class("lotus-title")
        self.lbl_sub = Gtk.Label(label=f"{eff_fw}", xalign=0)
        self.lbl_sub.get_style_context().add_class("lotus-subtitle")
        title_box.pack_start(lbl_title, False, False, 0)
        title_box.pack_start(self.lbl_sub, False, False, 0)
        header_box.pack_start(title_box, True, True, 0)

        btn_lang = Gtk.Button(label="EN" if self.lang == "vi" else "VI")
        btn_lang.get_style_context().add_class("lang-btn")
        btn_lang.set_valign(Gtk.Align.START)
        btn_lang.connect("clicked", self._on_toggle_lang)

        btn_close = Gtk.Button(label="✕")
        btn_close.set_relief(Gtk.ReliefStyle.NONE)
        btn_close.set_valign(Gtk.Align.START)
        btn_close.connect("clicked", lambda w: self.close())

        header_box.pack_end(btn_close, False, False, 0)
        header_box.pack_end(btn_lang, False, False, 0)
        main_box.pack_start(header_box, False, False, 0)

        # Enable Switch
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_enable = Gtk.Label(label=f"{tr(self.lang, 'qm_enable_vn')}:", xalign=0)
        lbl_enable.set_hexpand(True)
        self.sw_enable = Gtk.Switch()
        self.sw_enable.set_active(self.cfg.get("enabled", True))
        self.sw_enable.connect("notify::active", self._on_enable_toggled)
        switch_box.pack_start(lbl_enable, True, True, 0)
        switch_box.pack_end(self.sw_enable, False, False, 0)
        main_box.pack_start(switch_box, False, False, 2)

        # 1. Input Method (3 Pill Buttons on 1 row)
        im_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_im = Gtk.Label(label=f"{tr(self.lang, 'qm_input_method')}:", xalign=0)
        lbl_im.get_style_context().add_class("section-label")
        lbl_im.set_margin_end(4)

        self.btn_telex = Gtk.Button(label=tr(self.lang, "im_telex"))
        self.btn_telex.get_style_context().add_class("mode-btn")
        self.btn_telex.connect("clicked", lambda w: self._set_im(0))

        self.btn_vni = Gtk.Button(label=tr(self.lang, "im_vni"))
        self.btn_vni.get_style_context().add_class("mode-btn")
        self.btn_vni.connect("clicked", lambda w: self._set_im(1))

        self.btn_telex_vni = Gtk.Button(label=tr(self.lang, "im_telex_vni"))
        self.btn_telex_vni.get_style_context().add_class("mode-btn")
        self.btn_telex_vni.connect("clicked", lambda w: self._set_im(2))

        im_box.pack_start(lbl_im, False, False, 0)
        im_box.pack_start(self.btn_telex, True, True, 0)
        im_box.pack_start(self.btn_vni, True, True, 0)
        im_box.pack_start(self.btn_telex_vni, True, True, 0)
        main_box.pack_start(im_box, False, False, 2)

        # 2. Grid 2x2 Dropdowns (Charset, Output Mode, Tray Icon Style, Framework)
        combo_grid = Gtk.Grid()
        combo_grid.set_row_spacing(6)
        combo_grid.set_column_spacing(8)
        combo_grid.set_margin_top(4)
        combo_grid.set_margin_bottom(2)

        lbl_cs = Gtk.Label(label=f"{tr(self.lang, 'qm_charset')}:", xalign=0)
        lbl_cs.get_style_context().add_class("section-label")
        self.combo_cs = Gtk.ComboBoxText()
        for cid, label_key in [
            ("0", "qm_cs_unicode"),
            ("31", "qm_cs_combining"),
            ("27", "cs_tcvn3"),
            ("34", "cs_vni_win"),
        ]:
            self.combo_cs.append(cid, tr(self.lang, label_key))
        self.combo_cs.set_hexpand(True)
        self.combo_cs.connect("changed", self._on_cs_combo_changed)

        lbl_out = Gtk.Label(label=f"{tr(self.lang, 'qm_output_mode')}:", xalign=0)
        lbl_out.get_style_context().add_class("section-label")
        self.combo_out = Gtk.ComboBoxText()
        for oid, otext in [
            ("preedit", "Pre-edit"),
            ("surrounding", "Surrounding Text"),
            ("forward", "Forward Backspace"),
        ]:
            self.combo_out.append(oid, otext)
        self.combo_out.set_hexpand(True)
        self.combo_out.connect("changed", self._on_out_combo_changed)

        lbl_ic = Gtk.Label(label=f"{tr(self.lang, 'qm_icon_style')}:", xalign=0)
        lbl_ic.get_style_context().add_class("section-label")
        self.combo_ic = Gtk.ComboBoxText()
        for ic_id, label_key in [
            ("flag:us", "qm_ic_flag_us"),
            ("flag:uk", "qm_ic_flag_uk"),
            ("badge:us", "qm_ic_badge"),
            ("lotus:us", "qm_ic_lotus"),
            ("symbolic:us", "qm_ic_symbolic"),
        ]:
            self.combo_ic.append(ic_id, tr(self.lang, label_key))
        self.combo_ic.set_hexpand(True)
        self.combo_ic.connect("changed", self._on_ic_combo_changed)

        lbl_fw = Gtk.Label(label=f"{tr(self.lang, 'qm_framework')}:", xalign=0)
        lbl_fw.get_style_context().add_class("section-label")
        self.combo_fw = Gtk.ComboBoxText()
        for fid, ftext in [
            ("auto", tr(self.lang, "fw_auto")),
            ("ibus", "IBus"),
            ("fcitx5", "Fcitx5"),
            ("uinput", "UInput"),
        ]:
            self.combo_fw.append(fid, ftext)
        self.combo_fw.set_hexpand(True)
        self.combo_fw.connect("changed", self._on_fw_combo_changed)

        for combo in (self.combo_cs, self.combo_out, self.combo_ic, self.combo_fw):
            combo.connect("notify::popup-shown", self._on_combo_popup_shown)

        combo_grid.attach(lbl_cs, 0, 0, 1, 1)
        combo_grid.attach(self.combo_cs, 1, 0, 1, 1)
        combo_grid.attach(lbl_out, 2, 0, 1, 1)
        combo_grid.attach(self.combo_out, 3, 0, 1, 1)
        combo_grid.attach(lbl_ic, 0, 1, 1, 1)
        combo_grid.attach(self.combo_ic, 1, 1, 1, 1)
        combo_grid.attach(lbl_fw, 2, 1, 1, 1)
        combo_grid.attach(self.combo_fw, 3, 1, 1, 1)
        main_box.pack_start(combo_grid, False, False, 2)

        # 3. Quick Options (Grid 2x2 Checkboxes)
        lbl_opts = Gtk.Label(label=f"{tr(self.lang, 'qm_options')}:", xalign=0)
        lbl_opts.get_style_context().add_class("section-label")
        main_box.pack_start(lbl_opts, False, False, 0)

        opts_grid = Gtk.Grid()
        opts_grid.set_row_spacing(2)
        opts_grid.set_column_spacing(12)

        self.chk_bilingual = Gtk.CheckButton(label=tr(self.lang, "opt_bilingual"))
        self.chk_bilingual.set_active(self.cfg.get("auto_correct", True))
        self.chk_bilingual.connect("toggled", lambda w: self._toggle_opt("auto_correct", w.get_active()))

        self.chk_modern = Gtk.CheckButton(label=tr(self.lang, "opt_modern"))
        self.chk_modern.set_active(self.cfg.get("modern_tone_style", True))
        self.chk_modern.connect("toggled", lambda w: self._toggle_opt("modern_tone_style", w.get_active()))

        self.chk_macro = Gtk.CheckButton(label=tr(self.lang, "opt_macro_enable"))
        self.chk_macro.set_active(self.cfg.get("macro_enabled", True))
        self.chk_macro.connect("toggled", lambda w: self._toggle_opt("macro_enabled", w.get_active()))

        self.chk_w2u = Gtk.CheckButton(label=tr(self.lang, "opt_w2u"))
        self.chk_w2u.set_active(self.cfg.get("w2u", True))
        self.chk_w2u.connect("toggled", lambda w: self._toggle_opt("w2u", w.get_active()))

        opts_grid.attach(self.chk_bilingual, 0, 0, 1, 1)
        opts_grid.attach(self.chk_modern, 1, 0, 1, 1)
        opts_grid.attach(self.chk_macro, 0, 1, 1, 1)
        opts_grid.attach(self.chk_w2u, 1, 1, 1, 1)
        main_box.pack_start(opts_grid, False, False, 2)

        # 4. Footer Quick Launchers
        launch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        launch_box.set_margin_top(4)
        btn_conv = Gtk.Button(label=tr(self.lang, "qm_open_conv"))
        btn_conv.get_style_context().add_class("mode-btn")
        btn_conv.connect("clicked", lambda w: self._launch_setup("--converter"))

        btn_setup = Gtk.Button(label=tr(self.lang, "qm_open_setup"))
        btn_setup.get_style_context().add_class("mode-btn")
        btn_setup.connect("clicked", lambda w: self._launch_setup())

        launch_box.pack_start(btn_conv, True, True, 0)
        launch_box.pack_start(btn_setup, True, True, 0)
        main_box.pack_start(launch_box, False, False, 2)

        lbl_hint = Gtk.Label(label=tr(self.lang, "qm_hint"), xalign=0)
        lbl_hint.get_style_context().add_class("hint-bar")
        main_box.pack_start(lbl_hint, False, False, 2)

        self._update_buttons()
        self.root_box.show_all()

    def _launch_setup(self, extra_arg: str = None):
        setup_py = os.path.join(BASE_DIR, "ui", "setup_panel.py")
        cmd = [sys.executable, setup_py]
        if extra_arg:
            cmd.append(extra_arg)
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        self.close()

    def _on_toggle_lang(self, _btn):
        self.lang = "en" if self.lang == "vi" else "vi"
        self.cfg["ui_lang"] = self.lang
        self._save()
        self._build_content()

    def _on_combo_popup_shown(self, combo, _gparam):
        if not combo.get_property("popup-shown"):
            GLib.timeout_add(60, self._check_focus_and_close)

    def _on_focus_out(self, _widget, _event):
        GLib.timeout_add(60, self._check_focus_and_close)
        return False

    def _check_focus_and_close(self):
        if not self.get_visible():
            return False
        for combo in (
            getattr(self, "combo_cs", None),
            getattr(self, "combo_out", None),
            getattr(self, "combo_ic", None),
            getattr(self, "combo_fw", None),
        ):
            if combo is not None and combo.get_property("popup-shown"):
                return False
        if not self.has_toplevel_focus():
            self.close()
        return False

    def _update_buttons(self):
        self._updating_ui = True
        is_enabled = self.cfg.get("enabled", True)
        curr_ic = self.cfg.get("icon_style", "flag")
        curr_fv = self.cfg.get("flag_variant", "us")

        icon_p = DistroAdapter.get_status_icon_path(
            active=is_enabled, icon_style=curr_ic, flag_variant=curr_fv
        )
        if icon_p and os.path.exists(icon_p):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_p, 32, 32, True)
                self.hdr_icon.set_from_pixbuf(pb)
            except Exception:
                pass

        curr_im = self.cfg.get("input_method", 0)
        for btn, val in [(self.btn_telex, 0), (self.btn_vni, 1), (self.btn_telex_vni, 2)]:
            ctx = btn.get_style_context()
            if curr_im == val:
                ctx.add_class("active")
            else:
                ctx.remove_class("active")

        raw_cs = int(self.cfg.get("charset", 0))
        norm_cs = {9: 31, 5: 27, 12: 34}.get(raw_cs, raw_cs)
        cs_id = str(norm_cs) if str(norm_cs) in ("0", "31", "27", "34") else "0"
        self.combo_cs.set_active_id(cs_id)

        curr_out = str(self.cfg.get("output_mode", "preedit"))
        self.combo_out.set_active_id(
            curr_out if curr_out in ("preedit", "surrounding", "forward") else "preedit"
        )

        ic_key = f"{curr_ic}:{'uk' if (curr_ic == 'flag' and curr_fv == 'uk') else 'us'}"
        if not self.combo_ic.set_active_id(ic_key):
            self.combo_ic.set_active_id("flag:us")

        curr_fw = str(self.cfg.get("im_framework", "auto"))
        if not self.combo_fw.set_active_id(curr_fw):
            self.combo_fw.set_active_id("auto")

        eff_fw = resolve_effective_framework(curr_fw).upper()
        status_txt = tr(self.lang, "vn_status_on" if is_enabled else "vn_status_off")
        self.lbl_sub.set_text(f"{eff_fw} • {status_txt}")
        self._updating_ui = False

    def _on_cs_combo_changed(self, combo):
        if self._updating_ui:
            return
        cid = combo.get_active_id()
        if cid is not None:
            self._set_charset(int(cid))

    def _on_out_combo_changed(self, combo):
        if self._updating_ui:
            return
        oid = combo.get_active_id()
        if oid:
            self._set_out_mode(oid)

    def _on_ic_combo_changed(self, combo):
        if self._updating_ui:
            return
        ic_id = combo.get_active_id() or "flag:us"
        parts = ic_id.split(":", 1)
        st = parts[0]
        fv = parts[1] if len(parts) > 1 else "us"
        self._set_icon_style(st, fv)

    def _on_fw_combo_changed(self, combo):
        if self._updating_ui:
            return
        fid = combo.get_active_id()
        if fid:
            self._set_fw(fid)

    def _set_im(self, val):
        self.cfg["input_method"] = val
        self._save()
        self._update_buttons()

    def _set_charset(self, cs_val: int):
        self.cfg["charset"] = cs_val
        self._save()
        self._update_buttons()

    def _set_icon_style(self, st: str, fv: str):
        self.cfg["icon_style"] = st
        self.cfg["flag_variant"] = fv
        self._save()
        self._update_buttons()

    def _set_fw(self, fw):
        self.cfg["im_framework"] = fw
        self._save(switch_daemon=True)
        self._update_buttons()

    def _set_out_mode(self, mode):
        self.cfg["output_mode"] = mode
        self._save()
        self._update_buttons()

    def _toggle_opt(self, key, val):
        self.cfg[key] = val
        self._save()

    def _on_enable_toggled(self, switch, _gparam):
        self.cfg["enabled"] = switch.get_active()
        self._save()
        self._update_buttons()

    def _save(self, switch_daemon=False):
        save_config(self.cfg)
        apply_framework_config(self.cfg, switch_daemon=switch_daemon)
        if self.on_config_changed:
            self.on_config_changed(self.cfg)

    def _on_key_press(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            for combo in (
                getattr(self, "combo_cs", None),
                getattr(self, "combo_out", None),
                getattr(self, "combo_ic", None),
                getattr(self, "combo_fw", None),
            ):
                if combo is not None and combo.get_property("popup-shown"):
                    combo.popdown()
                    return True
            self.close()
            return True
        return False


def show_quick_menu():
    win = QuickMenuDialog()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.present()
    Gtk.main()


if __name__ == "__main__":
    show_quick_menu()
