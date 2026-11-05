#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Menu Dialog for Lotus Vietnamese Input Method.
Triggered by pressing ` (grave) or via status bar / shortcut.
Compact, modern floating dialog for GNOME Wayland.
"""

import sys
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.config_manager import load_config, save_config

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

CSS_DATA = b"""
window.quick-dialog {
    background-color: #1a1b26;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
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
    margin-bottom: 12px;
}

.section-label {
    font-size: 11px;
    font-weight: 600;
    color: #565f89;
    margin-top: 8px;
    margin-bottom: 4px;
}

button.mode-btn {
    background: #24283b;
    color: #a9b1d6;
    border: 1px solid #414868;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
    transition: all 150ms ease-in-out;
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

checkbutton {
    color: #c0caf5;
    font-size: 12px;
    margin-top: 2px;
    margin-bottom: 2px;
}

checkbutton:hover {
    color: #7aa2f7;
}

.hint-bar {
    font-size: 11px;
    color: #565f89;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 8px;
    margin-top: 10px;
}
"""

class QuickMenuDialog(Gtk.Window):
    def __init__(self, on_config_changed=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.on_config_changed = on_config_changed
        self.cfg = load_config()

        self.set_title("Bộ Gõ Lotus")
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_decorated(False)  # Frameless dialog
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)

        # Style context
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_DATA)
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.get_style_context().add_class("quick-dialog")

        # Container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        self.add(main_box)

        # Header with Lotus icon and Switch
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        lbl_title = Gtk.Label(label="🪷 LotusKey", xalign=0)
        lbl_title.get_style_context().add_class("lotus-title")
        lbl_sub = Gtk.Label(label="Quick Menu • Tác giả: Victor Pham", xalign=0)
        lbl_sub.get_style_context().add_class("lotus-subtitle")
        title_box.pack_start(lbl_title, False, False, 0)
        title_box.pack_start(lbl_sub, False, False, 0)
        header_box.pack_start(title_box, True, True, 0)

        # Close button
        btn_close = Gtk.Button(label="✕")
        btn_close.set_relief(Gtk.ReliefStyle.NONE)
        btn_close.connect("clicked", lambda w: self.close())
        header_box.pack_end(btn_close, False, False, 0)

        main_box.pack_start(header_box, False, False, 0)

        # Vietnamese Enable Switch
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_enable = Gtk.Label(label="Tiếng Việt (Ctrl+Shift / Alt+Z):", xalign=0)
        lbl_enable.set_hexpand(True)
        self.sw_enable = Gtk.Switch()
        self.sw_enable.set_active(self.cfg.get("enabled", True))
        self.sw_enable.connect("notify::active", self._on_enable_toggled)
        switch_box.pack_start(lbl_enable, True, True, 0)
        switch_box.pack_end(self.sw_enable, False, False, 0)
        main_box.pack_start(switch_box, False, False, 4)

        # Input Method section (Telex / VNI)
        lbl_im = Gtk.Label(label="Kiểu gõ:", xalign=0)
        lbl_im.get_style_context().add_class("section-label")
        main_box.pack_start(lbl_im, False, False, 0)

        im_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_telex = Gtk.Button(label="Telex")
        self.btn_telex.get_style_context().add_class("mode-btn")
        self.btn_telex.connect("clicked", lambda w: self._set_im(0))

        self.btn_vni = Gtk.Button(label="VNI")
        self.btn_vni.get_style_context().add_class("mode-btn")
        self.btn_vni.connect("clicked", lambda w: self._set_im(1))

        self.btn_telex_vni = Gtk.Button(label="Telex + VNI")
        self.btn_telex_vni.get_style_context().add_class("mode-btn")
        self.btn_telex_vni.connect("clicked", lambda w: self._set_im(2))

        im_box.pack_start(self.btn_telex, True, True, 0)
        im_box.pack_start(self.btn_vni, True, True, 0)
        im_box.pack_start(self.btn_telex_vni, True, True, 0)
        main_box.pack_start(im_box, False, False, 4)

        # Output Mode section
        lbl_mode = Gtk.Label(label="Chế độ gửi phím:", xalign=0)
        lbl_mode.get_style_context().add_class("section-label")
        main_box.pack_start(lbl_mode, False, False, 0)

        out_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_preedit = Gtk.Button(label="Pre-edit (Đệm Unikey)")
        self.btn_preedit.get_style_context().add_class("mode-btn")
        self.btn_preedit.connect("clicked", lambda w: self._set_out_mode("preedit"))

        self.btn_surrounding = Gtk.Button(label="Surrounding Text")
        self.btn_surrounding.get_style_context().add_class("mode-btn")
        self.btn_surrounding.connect("clicked", lambda w: self._set_out_mode("surrounding"))

        out_box.pack_start(self.btn_preedit, True, True, 0)
        out_box.pack_start(self.btn_surrounding, True, True, 0)
        main_box.pack_start(out_box, False, False, 4)

        # Tone & Typing Options
        lbl_opts = Gtk.Label(label="Tùy chọn nâng cao:", xalign=0)
        lbl_opts.get_style_context().add_class("section-label")
        main_box.pack_start(lbl_opts, False, False, 0)

        self.chk_modern = Gtk.CheckButton(label="Bỏ dấu kiểu mới (Modern Orthography: oà, uý)")
        self.chk_modern.set_active(self.cfg.get("modern_tone_style", True))
        self.chk_modern.connect("toggled", lambda w: self._toggle_opt("modern_tone_style", w.get_active()))
        main_box.pack_start(self.chk_modern, False, False, 0)

        self.chk_free = Gtk.CheckButton(label="Bỏ dấu tự do (Free-tone marking)")
        self.chk_free.set_active(self.cfg.get("free_tone_marking", True))
        self.chk_free.connect("toggled", lambda w: self._toggle_opt("free_tone_marking", w.get_active()))
        main_box.pack_start(self.chk_free, False, False, 0)

        self.chk_w2u = Gtk.CheckButton(label="Gõ nhanh W thành Ư (W to Ư)")
        self.chk_w2u.set_active(self.cfg.get("w2u", True))
        self.chk_w2u.connect("toggled", lambda w: self._toggle_opt("w2u", w.get_active()))
        main_box.pack_start(self.chk_w2u, False, False, 0)

        # Hint footer
        lbl_hint = Gtk.Label(
            label="Phím tắt: Bấm ` mở Quick Menu • Ctrl+Shift hoặc Alt+Z chuyển Anh/Việt • ESC đóng",
            xalign=0
        )
        lbl_hint.get_style_context().add_class("hint-bar")
        main_box.pack_start(lbl_hint, False, False, 4)

        self.connect("key-press-event", self._on_key_press)
        self.connect("focus-out-event", self._on_focus_out)
        self._update_buttons()

    def _on_focus_out(self, widget, event):
        self.close()
        return False

    def _update_buttons(self):
        curr_im = self.cfg.get("input_method", 0)
        for btn, val in [(self.btn_telex, 0), (self.btn_vni, 1), (self.btn_telex_vni, 2)]:
            ctx = btn.get_style_context()
            if curr_im == val:
                ctx.add_class("active")
            else:
                ctx.remove_class("active")

        curr_out = self.cfg.get("output_mode", "surrounding")
        for btn, val in [(self.btn_surrounding, "surrounding"), (self.btn_preedit, "preedit")]:
            ctx = btn.get_style_context()
            if curr_out == val:
                ctx.add_class("active")
            else:
                ctx.remove_class("active")

    def _set_im(self, val):
        self.cfg["input_method"] = val
        self._save()
        self._update_buttons()

    def _set_out_mode(self, mode):
        self.cfg["output_mode"] = mode
        self._save()
        self._update_buttons()

    def _toggle_opt(self, key, val):
        self.cfg[key] = val
        self._save()

    def _on_enable_toggled(self, switch, gparam):
        self.cfg["enabled"] = switch.get_active()
        self._save()

    def _save(self):
        save_config(self.cfg)
        target_engine = "lotuskey-vni" if self.cfg.get("input_method") == 1 else "lotuskey"
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.input-sources", "sources", f"[('ibus', '{target_engine}'), ('xkb', 'us')]"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            subprocess.run(
                ["ibus", "engine", target_engine],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass
        try:
            subprocess.run(["pkill", "-USR1", "-f", "ibus-engine-lotus"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        if self.on_config_changed:
            self.on_config_changed(self.cfg)

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

def show_quick_menu():
    win = QuickMenuDialog()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.present()
    Gtk.main()

if __name__ == '__main__':
    show_quick_menu()
