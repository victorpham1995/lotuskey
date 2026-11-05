#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Control Panel (Bảng điều khiển)
Clean, concise Vietnamese UI with preserved technical English terms.
"""

import sys
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.config_manager import load_config, save_config

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class SetupPanel(Gtk.Window):
    def __init__(self):
        super().__init__(title="LotusKey - Bảng điều khiển")
        self.set_default_size(440, 520)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.cfg = load_config()

        self.connect("delete-event", self._on_delete_event)
        self.connect("key-press-event", self._on_key_press)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_border_width(18)
        self.add(main_box)

        # Title Box
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label(
            label="<span size='large' weight='bold'>🪷 LotusKey</span>",
            use_markup=True,
            xalign=0
        )
        lbl_sub = Gtk.Label(
            label="<span size='small' foreground='#565f89'>Bộ gõ tiếng Việt Native cho GNOME Wayland • Tác giả: <b>Victor Pham</b></span>",
            use_markup=True,
            xalign=0
        )
        title_box.pack_start(lbl_title, False, False, 0)
        title_box.pack_start(lbl_sub, False, False, 0)
        main_box.pack_start(title_box, False, False, 0)

        # Frame: Điều khiển chính
        frame_main = Gtk.Frame(label=" Điều khiển chính ")
        grid_main = Gtk.Grid()
        grid_main.set_border_width(12)
        grid_main.set_row_spacing(10)
        grid_main.set_column_spacing(14)
        frame_main.add(grid_main)

        # 1. Bảng mã
        lbl_cs = Gtk.Label(label="Bảng mã:", xalign=0)
        self.combo_cs = Gtk.ComboBoxText()
        charsets = [
            (0, "Unicode (UTF-8 dựng sẵn)"),
            (31, "Unicode Tổ hợp"),
            (27, "TCVN3 (ABC)"),
            (34, "VNI Windows"),
        ]
        curr_cs = self.cfg.get("charset", 0)
        for idx, (cid, name) in enumerate(charsets):
            self.combo_cs.append_text(name)
            if cid == curr_cs:
                self.combo_cs.set_active(idx)
        if self.combo_cs.get_active() < 0:
            self.combo_cs.set_active(0)
        grid_main.attach(lbl_cs, 0, 0, 1, 1)
        grid_main.attach(self.combo_cs, 1, 0, 1, 1)

        # 2. Kiểu gõ
        lbl_im = Gtk.Label(label="Kiểu gõ:", xalign=0)
        self.combo_im = Gtk.ComboBoxText()
        methods = ["Telex", "VNI", "Telex + VNI"]
        for m in methods:
            self.combo_im.append_text(m)
        curr_im = self.cfg.get("input_method", 0)
        if 0 <= curr_im < len(methods):
            self.combo_im.set_active(curr_im)
        else:
            self.combo_im.set_active(0)
        grid_main.attach(lbl_im, 0, 1, 1, 1)
        grid_main.attach(self.combo_im, 1, 1, 1, 1)

        # 3. Phím chuyển Anh/Việt
        lbl_toggle = Gtk.Label(label="Phím chuyển:", xalign=0)
        self.combo_toggle = Gtk.ComboBoxText()
        toggles = [
            ("Both", "Ctrl + Shift & Alt + Z (Mặc định)"),
            ("Control+Shift", "Control + Shift"),
            ("Alt+Z", "Alt + Z"),
            ("Shift+Space", "Shift + Space"),
            ("None", "Không dùng phím tắt"),
        ]
        curr_toggle = self.cfg.get("toggle_key", "Both")
        for idx, (val, name) in enumerate(toggles):
            self.combo_toggle.append_text(name)
            if val == curr_toggle:
                self.combo_toggle.set_active(idx)
        if self.combo_toggle.get_active() < 0:
            self.combo_toggle.set_active(0)
        grid_main.attach(lbl_toggle, 0, 2, 1, 1)
        grid_main.attach(self.combo_toggle, 1, 2, 1, 1)

        main_box.pack_start(frame_main, False, False, 0)

        # Frame: Chế độ xử lý ký tự (Wayland / X11)
        frame_engine = Gtk.Frame(label=" Chế độ xử lý ký tự (Wayland & X11) ")
        box_engine = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box_engine.set_border_width(12)
        frame_engine.add(box_engine)

        self.rb_preedit = Gtk.RadioButton.new_with_label(
            None, "Pre-edit (Khuyên dùng - Đệm Unikey tương thích tốt Wayland/Electron)"
        )
        self.rb_surrounding = Gtk.RadioButton.new_with_label_from_widget(
            self.rb_preedit, "Surrounding Text (Mượt mà cho GNOME và trình duyệt)"
        )
        self.rb_forward = Gtk.RadioButton.new_with_label_from_widget(
            self.rb_preedit, "Forward Backspace (Cho Terminal cổ điển)"
        )

        curr_mode = self.cfg.get("output_mode", "preedit")
        if curr_mode == "surrounding":
            self.rb_surrounding.set_active(True)
        elif curr_mode == "forward":
            self.rb_forward.set_active(True)
        else:
            self.rb_preedit.set_active(True)

        box_engine.pack_start(self.rb_preedit, False, False, 0)
        box_engine.pack_start(self.rb_surrounding, False, False, 0)
        box_engine.pack_start(self.rb_forward, False, False, 0)

        main_box.pack_start(frame_engine, False, False, 0)

        # Frame: Tùy chọn nâng cao
        frame_adv = Gtk.Frame(label=" Tùy chọn nâng cao ")
        box_adv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box_adv.set_border_width(12)
        frame_adv.add(box_adv)

        self.chk_modern = Gtk.CheckButton(label="Bỏ dấu kiểu mới (Modern Orthography: oà, uý)")
        self.chk_modern.set_active(self.cfg.get("modern_tone_style", True))
        box_adv.pack_start(self.chk_modern, False, False, 0)

        self.chk_free = Gtk.CheckButton(label="Bỏ dấu tự do (Free-tone marking)")
        self.chk_free.set_active(self.cfg.get("free_tone_marking", True))
        box_adv.pack_start(self.chk_free, False, False, 0)

        self.chk_w2u = Gtk.CheckButton(label="Gõ nhanh W thành Ư (W to Ư)")
        self.chk_w2u.set_active(self.cfg.get("w2u", True))
        box_adv.pack_start(self.chk_w2u, False, False, 0)

        self.chk_bracket = Gtk.CheckButton(label="Gõ nhanh [ thành ơ và ] thành ư (Bracket transform)")
        self.chk_bracket.set_active(self.cfg.get("bracket_transform", True))
        box_adv.pack_start(self.chk_bracket, False, False, 0)

        self.chk_menu_grave = Gtk.CheckButton(label="Phím ` (grave) mở nhanh Quick Menu")
        self.chk_menu_grave.set_active(self.cfg.get("mode_menu_key", "grave") == "grave")
        box_adv.pack_start(self.chk_menu_grave, False, False, 0)

        self.chk_autostart = Gtk.CheckButton(label="Khởi động cùng hệ thống (Autostart with OS)")
        self.chk_autostart.set_active(self.cfg.get("autostart", True))
        box_adv.pack_start(self.chk_autostart, False, False, 0)

        main_box.pack_start(frame_adv, False, False, 0)

        # Buttons Box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.END)

        btn_save = Gtk.Button(label="Áp dụng & Lưu")
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", lambda w: self._on_save_clicked())

        btn_close = Gtk.Button(label="Đóng")
        btn_close.connect("clicked", lambda w: self._on_close_clicked())

        btn_box.pack_start(btn_save, False, False, 0)
        btn_box.pack_start(btn_close, False, False, 0)
        main_box.pack_start(btn_box, False, False, 0)

    def _collect_data(self):
        cs_map = [0, 31, 27, 34]
        cs_idx = self.combo_cs.get_active()
        self.cfg["charset"] = cs_map[cs_idx] if 0 <= cs_idx < len(cs_map) else 0

        im_idx = self.combo_im.get_active()
        self.cfg["input_method"] = im_idx if im_idx >= 0 else 0

        tg_idx = self.combo_toggle.get_active()
        tg_map = ["Both", "Control+Shift", "Alt+Z", "Shift+Space", "None"]
        self.cfg["toggle_key"] = tg_map[tg_idx] if 0 <= tg_idx < len(tg_map) else "Both"

        if self.rb_preedit.get_active():
            self.cfg["output_mode"] = "preedit"
        elif self.rb_forward.get_active():
            self.cfg["output_mode"] = "forward"
        else:
            self.cfg["output_mode"] = "surrounding"

        self.cfg["modern_tone_style"] = self.chk_modern.get_active()
        self.cfg["free_tone_marking"] = self.chk_free.get_active()
        self.cfg["w2u"] = self.chk_w2u.get_active()
        self.cfg["bracket_transform"] = self.chk_bracket.get_active()
        self.cfg["mode_menu_key"] = "grave" if self.chk_menu_grave.get_active() else "None"
        self.cfg["autostart"] = self.chk_autostart.get_active()

    def _apply_and_save(self, notify=True):
        self._collect_data()
        save_config(self.cfg)

        # Sync input method engine with GNOME & IBus (support both lotuskey and lotus names)
        target_engine = "lotuskey-vni" if self.cfg.get("input_method") == 1 else "lotuskey"
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.input-sources", "sources", f"[('ibus', '{target_engine}'), ('xkb', 'us')]"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.input-sources", "mru-sources", f"[('ibus', '{target_engine}'), ('xkb', 'us')]"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            subprocess.run(
                ["ibus", "engine", target_engine],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

        # Signal running ibus-engine-lotuskey / ibus-engine-lotus to hot-reload configuration
        try:
            subprocess.run(["pkill", "-USR1", "-f", "ibus-engine-lotus"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        # Visual notification feedback
        if notify:
            im_label = "VNI" if self.cfg.get("input_method") == 1 else "Telex"
            tg_label = self.cfg.get("toggle_key", "Both")
            try:
                subprocess.Popen([
                    "notify-send", "-t", "1800",
                    "-h", "string:x-canonical-private-synchronous:lotus-config",
                    "-i", "/usr/share/icons/hicolor/scalable/apps/fcitx-lotus.svg",
                    "LotusKey",
                    f"✓ Đã lưu cài đặt!\nKiểu gõ: {im_label} • Phím chuyển: {tg_label}"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def _on_save_clicked(self):
        self._apply_and_save(notify=True)
        self.close()

    def _on_close_clicked(self):
        # Auto-save changes on Close button click
        self._apply_and_save(notify=False)
        self.close()

    def _on_delete_event(self, widget, event):
        # Auto-save changes when window 'X' is clicked
        self._apply_and_save(notify=False)
        return False

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self._apply_and_save(notify=False)
            self.close()
            return True
        return False

def main():
    win = SetupPanel()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.present()
    Gtk.main()

if __name__ == '__main__':
    main()
