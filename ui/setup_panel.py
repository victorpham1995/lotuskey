#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Settings Panel
Supports Vietnamese and English UI, Multi-Framework IME selection, and Macro Editor.
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.config_manager import load_config, save_config, load_macros, save_macros
from config.distro_adapter import DistroAdapter
from config.i18n import normalize_lang, tr
from config.im_framework import (
    SUPPORTED_FRAMEWORKS,
    apply_framework_config,
    detect_desktop_environment,
    detect_installed_frameworks,
    resolve_effective_framework,
)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk


class SetupPanel(Gtk.Window):
    def __init__(self):
        self.cfg = load_config()
        self.macros = load_macros()
        self.lang = normalize_lang(self.cfg.get("ui_lang", "vi"))
        self._building_ui = False

        super().__init__(title=tr(self.lang, "settings_title"))
        self.set_default_size(500, 580)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.connect("delete-event", self._on_delete_event)
        self.connect("key-press-event", self._on_key_press)

        self.root_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.root_container)
        self._rebuild_ui()

    def _rebuild_ui(self, active_tab: int = 0):
        self._building_ui = True
        for child in self.root_container.get_children():
            self.root_container.remove(child)

        self.set_title(tr(self.lang, "settings_title"))

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_border_width(16)
        self.root_container.pack_start(main_box, True, True, 0)

        # Header with title, system summary, and language switcher
        env_info = detect_desktop_environment()
        distro_info = DistroAdapter.detect_distro()
        eff_fw = resolve_effective_framework(self.cfg.get("im_framework", "auto")).upper()

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        lbl_title = Gtk.Label(
            label="<span size='large' weight='bold'>LotusKey</span>",
            use_markup=True,
            xalign=0,
        )
        lbl_sub = Gtk.Label(
            label=(
                f"<span size='small' foreground='#565f89'>"
                f"{distro_info['name']} • {env_info['desktop']} ({env_info['session_type'].upper()}) • {eff_fw}"
                f"</span>"
            ),
            use_markup=True,
            xalign=0,
        )
        title_box.pack_start(lbl_title, False, False, 0)
        title_box.pack_start(lbl_sub, False, False, 0)
        header_row.pack_start(title_box, True, True, 0)

        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_lang = Gtk.Label(label=tr(self.lang, "ui_lang_label"), xalign=1)
        self.combo_lang = Gtk.ComboBoxText()
        self.combo_lang.append_text("Tiếng Việt")
        self.combo_lang.append_text("English")
        self.combo_lang.set_active(1 if self.lang == "en" else 0)
        self.combo_lang.connect("changed", self._on_lang_changed)
        lang_box.pack_start(lbl_lang, False, False, 0)
        lang_box.pack_start(self.combo_lang, False, False, 0)
        header_row.pack_end(lang_box, False, False, 0)

        main_box.pack_start(header_row, False, False, 0)

        # Notebook tabs
        self.notebook = Gtk.Notebook()
        main_box.pack_start(self.notebook, True, True, 0)

        self._build_general_tab()
        self._build_macro_tab()

        # Action buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)

        btn_save = Gtk.Button(label=tr(self.lang, "save"))
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", lambda w: self._on_save_clicked())

        btn_close = Gtk.Button(label=tr(self.lang, "close"))
        btn_close.connect("clicked", lambda w: self._on_close_clicked())

        btn_box.pack_start(btn_save, False, False, 0)
        btn_box.pack_start(btn_close, False, False, 0)
        main_box.pack_start(btn_box, False, False, 0)

        self.root_container.show_all()
        self.notebook.set_current_page(active_tab)
        self._building_ui = False

    def _build_general_tab(self):
        tab_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab_box.set_border_width(12)

        # Frame 1: Input Method
        frame_main = Gtk.Frame(label=tr(self.lang, "frame_main"))
        grid_main = Gtk.Grid()
        grid_main.set_border_width(12)
        grid_main.set_row_spacing(8)
        grid_main.set_column_spacing(14)
        frame_main.add(grid_main)

        # 0. Backend Framework
        lbl_fw = Gtk.Label(label=tr(self.lang, "lbl_framework"), xalign=0)
        self.combo_fw = Gtk.ComboBoxText()
        curr_fw = self.cfg.get("im_framework", "auto")
        installed_fws = detect_installed_frameworks()
        fw_keys = [
            ("auto", tr(self.lang, "fw_auto")),
            ("ibus", tr(self.lang, "fw_ibus")),
            ("fcitx5", tr(self.lang, "fw_fcitx5")),
            ("fcitx", tr(self.lang, "fw_fcitx")),
            ("uinput", tr(self.lang, "fw_uinput")),
        ]
        for idx, (fw_id, fw_label) in enumerate(fw_keys):
            if fw_id != "auto":
                is_inst = installed_fws.get(fw_id, {}).get("installed", False)
                status = tr(self.lang, "installed_tag") if is_inst else tr(self.lang, "not_installed_tag")
                self.combo_fw.append_text(f"{fw_label} ({status})")
            else:
                eff = resolve_effective_framework("auto").upper()
                self.combo_fw.append_text(f"{fw_label} ({eff})")
            if fw_id == curr_fw:
                self.combo_fw.set_active(idx)
        if self.combo_fw.get_active() < 0:
            self.combo_fw.set_active(0)
        self.combo_fw.set_hexpand(True)
        grid_main.attach(lbl_fw, 0, 0, 1, 1)
        grid_main.attach(self.combo_fw, 1, 0, 1, 1)

        # 1. Charset
        lbl_cs = Gtk.Label(label=tr(self.lang, "lbl_charset"), xalign=0)
        self.combo_cs = Gtk.ComboBoxText()
        charsets = [
            (0, tr(self.lang, "cs_unicode")),
            (31, tr(self.lang, "cs_combining")),
            (27, tr(self.lang, "cs_tcvn3")),
            (34, tr(self.lang, "cs_vni_win")),
        ]
        curr_cs = self.cfg.get("charset", 0)
        for idx, (cid, name) in enumerate(charsets):
            self.combo_cs.append_text(name)
            if cid == curr_cs:
                self.combo_cs.set_active(idx)
        if self.combo_cs.get_active() < 0:
            self.combo_cs.set_active(0)
        self.combo_cs.set_hexpand(True)
        grid_main.attach(lbl_cs, 0, 1, 1, 1)
        grid_main.attach(self.combo_cs, 1, 1, 1, 1)

        # 2. Input Method
        lbl_im = Gtk.Label(label=tr(self.lang, "lbl_input_method"), xalign=0)
        self.combo_im = Gtk.ComboBoxText()
        methods = [
            tr(self.lang, "im_telex"),
            tr(self.lang, "im_vni"),
            tr(self.lang, "im_telex_vni"),
        ]
        for m in methods:
            self.combo_im.append_text(m)
        curr_im = self.cfg.get("input_method", 0)
        self.combo_im.set_active(curr_im if 0 <= curr_im < len(methods) else 0)
        self.combo_im.set_hexpand(True)
        grid_main.attach(lbl_im, 0, 2, 1, 1)
        grid_main.attach(self.combo_im, 1, 2, 1, 1)

        # 3. Toggle Key
        lbl_toggle = Gtk.Label(label=tr(self.lang, "lbl_toggle_key"), xalign=0)
        self.combo_toggle = Gtk.ComboBoxText()
        toggles = [
            ("Both", tr(self.lang, "tg_both")),
            ("Control+Shift", tr(self.lang, "tg_ctrl_shift")),
            ("Alt+Z", tr(self.lang, "tg_alt_z")),
            ("Shift+Space", tr(self.lang, "tg_shift_space")),
            ("None", tr(self.lang, "tg_none")),
        ]
        curr_toggle = self.cfg.get("toggle_key", "Both")
        for idx, (val, name) in enumerate(toggles):
            self.combo_toggle.append_text(name)
            if val == curr_toggle:
                self.combo_toggle.set_active(idx)
        if self.combo_toggle.get_active() < 0:
            self.combo_toggle.set_active(0)
        self.combo_toggle.set_hexpand(True)
        grid_main.attach(lbl_toggle, 0, 3, 1, 1)
        grid_main.attach(self.combo_toggle, 1, 3, 1, 1)

        tab_box.pack_start(frame_main, False, False, 0)

        # Frame 2: Output Mode
        frame_engine = Gtk.Frame(label=tr(self.lang, "frame_output"))
        box_engine = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box_engine.set_border_width(10)
        frame_engine.add(box_engine)

        self.rb_preedit = Gtk.RadioButton.new_with_label(None, tr(self.lang, "out_preedit"))
        self.rb_surrounding = Gtk.RadioButton.new_with_label_from_widget(
            self.rb_preedit, tr(self.lang, "out_surrounding")
        )
        self.rb_forward = Gtk.RadioButton.new_with_label_from_widget(
            self.rb_preedit, tr(self.lang, "out_forward")
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

        tab_box.pack_start(frame_engine, False, False, 0)

        # Frame 3: Typing Options
        frame_adv = Gtk.Frame(label=tr(self.lang, "frame_options"))
        box_adv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_adv.set_border_width(10)
        frame_adv.add(box_adv)

        self.chk_bilingual = Gtk.CheckButton(label=tr(self.lang, "opt_bilingual"))
        self.chk_bilingual.set_active(self.cfg.get("auto_correct", True))
        box_adv.pack_start(self.chk_bilingual, False, False, 0)

        self.chk_modern = Gtk.CheckButton(label=tr(self.lang, "opt_modern"))
        self.chk_modern.set_active(self.cfg.get("modern_tone_style", True))
        box_adv.pack_start(self.chk_modern, False, False, 0)

        self.chk_free = Gtk.CheckButton(label=tr(self.lang, "opt_free_tone"))
        self.chk_free.set_active(self.cfg.get("free_tone_marking", True))
        box_adv.pack_start(self.chk_free, False, False, 0)

        self.chk_quick_telex = Gtk.CheckButton(label=tr(self.lang, "opt_quick_telex"))
        self.chk_quick_telex.set_active(self.cfg.get("quick_telex", False))
        box_adv.pack_start(self.chk_quick_telex, False, False, 0)

        self.chk_w2u = Gtk.CheckButton(label=tr(self.lang, "opt_w2u"))
        self.chk_w2u.set_active(self.cfg.get("w2u", True))
        box_adv.pack_start(self.chk_w2u, False, False, 0)

        self.chk_bracket = Gtk.CheckButton(label=tr(self.lang, "opt_bracket"))
        self.chk_bracket.set_active(self.cfg.get("bracket_transform", True))
        box_adv.pack_start(self.chk_bracket, False, False, 0)

        self.chk_underline = Gtk.CheckButton(label=tr(self.lang, "opt_underline"))
        self.chk_underline.set_active(self.cfg.get("preedit_underline", False))
        box_adv.pack_start(self.chk_underline, False, False, 0)

        self.chk_menu_grave = Gtk.CheckButton(label=tr(self.lang, "opt_grave_menu"))
        self.chk_menu_grave.set_active(self.cfg.get("mode_menu_key", "grave") == "grave")
        box_adv.pack_start(self.chk_menu_grave, False, False, 0)

        self.chk_autostart = Gtk.CheckButton(label=tr(self.lang, "opt_autostart"))
        self.chk_autostart.set_active(self.cfg.get("autostart", True))
        box_adv.pack_start(self.chk_autostart, False, False, 0)

        tab_box.pack_start(frame_adv, False, False, 0)

        self.notebook.append_page(tab_box, Gtk.Label(label=tr(self.lang, "tab_general")))

    def _build_macro_tab(self):
        macro_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        macro_box.set_border_width(12)

        self.chk_macro_enabled = Gtk.CheckButton(label=tr(self.lang, "opt_macro_enable"))
        self.chk_macro_enabled.set_active(self.cfg.get("macro_enabled", True))
        macro_box.pack_start(self.chk_macro_enabled, False, False, 0)

        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.entry_macro_key = Gtk.Entry()
        self.entry_macro_key.set_placeholder_text(tr(self.lang, "ph_macro_key"))
        self.entry_macro_key.set_width_chars(14)

        self.entry_macro_val = Gtk.Entry()
        self.entry_macro_val.set_placeholder_text(tr(self.lang, "ph_macro_val"))
        self.entry_macro_val.set_hexpand(True)
        self.entry_macro_val.connect("activate", lambda w: self._on_add_macro())

        btn_add = Gtk.Button(label=tr(self.lang, "btn_macro_add"))
        btn_add.connect("clicked", lambda w: self._on_add_macro())

        btn_del = Gtk.Button(label=tr(self.lang, "btn_macro_del"))
        btn_del.connect("clicked", lambda w: self._on_delete_macro())

        entry_box.pack_start(self.entry_macro_key, False, False, 0)
        entry_box.pack_start(self.entry_macro_val, True, True, 0)
        entry_box.pack_start(btn_add, False, False, 0)
        entry_box.pack_start(btn_del, False, False, 0)
        macro_box.pack_start(entry_box, False, False, 0)

        self.macro_store = Gtk.ListStore(str, str)
        for item in self.macros:
            self.macro_store.append([item.get("key", ""), item.get("value", "")])

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_shadow_type(Gtk.ShadowType.IN)

        self.macro_tree = Gtk.TreeView(model=self.macro_store)
        renderer_key = Gtk.CellRendererText()
        col_key = Gtk.TreeViewColumn(tr(self.lang, "col_macro_key"), renderer_key, text=0)
        col_key.set_min_width(120)
        self.macro_tree.append_column(col_key)

        renderer_val = Gtk.CellRendererText()
        col_val = Gtk.TreeViewColumn(tr(self.lang, "col_macro_val"), renderer_val, text=1)
        col_val.set_expand(True)
        self.macro_tree.append_column(col_val)

        selection = self.macro_tree.get_selection()
        selection.connect("changed", self._on_macro_row_selected)

        scroll.add(self.macro_tree)
        macro_box.pack_start(scroll, True, True, 0)

        self.notebook.append_page(macro_box, Gtk.Label(label=tr(self.lang, "tab_macro")))

    def _on_lang_changed(self, combo):
        if self._building_ui:
            return
        curr_tab = self.notebook.get_current_page() if hasattr(self, "notebook") else 0
        self._collect_data()
        self.lang = "en" if combo.get_active() == 1 else "vi"
        self.cfg["ui_lang"] = self.lang
        self._rebuild_ui(active_tab=curr_tab)

    def _on_macro_row_selected(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            self.entry_macro_key.set_text(model[treeiter][0])
            self.entry_macro_val.set_text(model[treeiter][1])

    def _on_add_macro(self):
        k = self.entry_macro_key.get_text().strip()
        v = self.entry_macro_val.get_text().strip()
        if not k or not v or " " in k or "=" in k:
            return
        for row in self.macro_store:
            if row[0].lower() == k.lower():
                row[0] = k
                row[1] = v
                self.entry_macro_key.set_text("")
                self.entry_macro_val.set_text("")
                return
        self.macro_store.append([k, v])
        self.entry_macro_key.set_text("")
        self.entry_macro_val.set_text("")

    def _on_delete_macro(self):
        selection = self.macro_tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            model.remove(treeiter)
            self.entry_macro_key.set_text("")
            self.entry_macro_val.set_text("")

    def _collect_data(self):
        self.cfg["ui_lang"] = self.lang

        fw_idx = self.combo_fw.get_active()
        if 0 <= fw_idx < len(SUPPORTED_FRAMEWORKS):
            self.cfg["im_framework"] = SUPPORTED_FRAMEWORKS[fw_idx][0]
        else:
            self.cfg["im_framework"] = "auto"

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

        self.cfg["auto_correct"] = self.chk_bilingual.get_active()
        self.cfg["modern_tone_style"] = self.chk_modern.get_active()
        self.cfg["free_tone_marking"] = self.chk_free.get_active()
        self.cfg["quick_telex"] = self.chk_quick_telex.get_active()
        self.cfg["w2u"] = self.chk_w2u.get_active()
        self.cfg["bracket_transform"] = self.chk_bracket.get_active()
        self.cfg["preedit_underline"] = self.chk_underline.get_active()
        self.cfg["mode_menu_key"] = "grave" if self.chk_menu_grave.get_active() else "None"
        self.cfg["autostart"] = self.chk_autostart.get_active()
        self.cfg["macro_enabled"] = self.chk_macro_enabled.get_active()

        self.macros = [{"key": row[0], "value": row[1]} for row in self.macro_store]

    def _apply_and_save(self, notify=True):
        self._collect_data()
        save_macros(self.macros)
        save_config(self.cfg)

        effective_fw = apply_framework_config(self.cfg, self.macros, switch_daemon=True)

        if notify:
            im_idx = self.cfg.get("input_method", 0)
            im_label = "VNI" if im_idx == 1 else ("Telex+VNI" if im_idx == 2 else "Telex")
            tg_label = self.cfg.get("toggle_key", "Both")
            body = tr(self.lang, "notify_saved_body", fw=effective_fw.upper(), im=im_label, tg=tg_label)
            try:
                subprocess.Popen(
                    [
                        "notify-send",
                        "-t",
                        "1600",
                        "-h",
                        "string:x-canonical-private-synchronous:lotus-config",
                        "-i",
                        DistroAdapter.get_icon_path(active=True),
                        "LotusKey",
                        body,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

    def _on_save_clicked(self):
        self._apply_and_save(notify=True)
        self.close()

    def _on_close_clicked(self):
        self._apply_and_save(notify=False)
        self.close()

    def _on_delete_event(self, widget, event):
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


if __name__ == "__main__":
    main()
