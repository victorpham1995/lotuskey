#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Settings Panel & Bidirectional Clipboard Charset Converter
Features:
  - Flat Flag Icon Preview (VN / US / UK), V/E Badge, Lotus, Symbolic
  - Compact Mode <-> Advanced Mode (4 Tabs: Typing Rules, Macros, Applications, System & Theme)
  - Macro Search Filter + UniKey/EVKey (.txt) & LotusKey (.json) Import/Export
  - Bidirectional Clipboard & Text Charset Converter (Unicode NFC <-> TCVN3 <-> VNI <-> Combining <-> ASCII)
  - Distinct Save, Cancel (Esc), and Reset Defaults actions
"""

import copy
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.config_manager import (
    DEFAULT_CONFIG,
    DEFAULT_EXCLUDED_APPS,
    convert_vietnamese_text,
    export_macros_to_file,
    import_macros_from_file,
    load_config,
    load_macros,
    save_config,
    save_macros,
)
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
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gtk

PANEL_CSS_DARK = b"""
.lotus-header-card {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 10px;
    padding: 10px 14px;
}
.lotus-status-on {
    color: #73daca;
    font-weight: 700;
}
.lotus-status-off {
    color: #a9b1d6;
    font-weight: 600;
}
.lotus-expand-btn {
    font-weight: 600;
    padding: 6px 10px;
}
"""

PANEL_CSS_LIGHT = b"""
.lotus-header-card {
    background-color: rgba(0, 0, 0, 0.03);
    border: 1px solid rgba(0, 0, 0, 0.10);
    border-radius: 10px;
    padding: 10px 14px;
}
.lotus-status-on {
    color: #d81b60;
    font-weight: 700;
}
.lotus-status-off {
    color: #546e7a;
    font-weight: 600;
}
.lotus-expand-btn {
    font-weight: 600;
    padding: 6px 10px;
}
"""

_css_provider = None


def apply_app_theme(theme_mode: str = "auto") -> None:
    global _css_provider
    settings = Gtk.Settings.get_default()
    mode = (theme_mode or "auto").lower()
    use_dark = False
    if settings is not None:
        if mode == "dark":
            settings.set_property("gtk-application-prefer-dark-theme", True)
            use_dark = True
        elif mode == "light":
            settings.set_property("gtk-application-prefer-dark-theme", False)
            use_dark = False
        else:
            gtk_theme = str(settings.get_property("gtk-theme-name") or "").lower()
            use_dark = "dark" in gtk_theme or bool(settings.get_property("gtk-application-prefer-dark-theme"))

    screen = Gdk.Screen.get_default()
    if screen is not None:
        if _css_provider is None:
            _css_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(
                screen, _css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        _css_provider.load_from_data(PANEL_CSS_DARK if use_dark else PANEL_CSS_LIGHT)


def load_svg_pixbuf(path: str, size: int = 32):
    if path and os.path.exists(path):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
        except Exception:
            pass
    return None


class CharsetConverterDialog(Gtk.Dialog):
    """Bidirectional Vietnamese Charset Converter for Clipboard & Text."""

    CHARSET_ITEMS = [
        ("unicode", "cs_unicode"),
        ("tcvn3", "cs_tcvn3"),
        ("vni", "cs_vni_win"),
        ("combining", "cs_combining"),
    ]
    DST_CHARSET_ITEMS = CHARSET_ITEMS + [("ascii", "cs_ascii")]
    CASE_ITEMS = [
        ("none", "case_none"),
        ("upper", "case_upper"),
        ("lower", "case_lower"),
        ("title", "case_title"),
    ]

    def __init__(self, parent=None, lang: str = "vi"):
        super().__init__(
            title=tr(lang, "conv_title"),
            transient_for=parent,
            flags=0,
        )
        self.lang = normalize_lang(lang)
        self.set_default_size(560, 420)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT if parent else Gtk.WindowPosition.CENTER)

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_border_width(14)

        # Row 1: Source & Target Charset + Swap
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(10)

        lbl_src = Gtk.Label(label=tr(self.lang, "conv_src_label"), xalign=0)
        self.combo_src = Gtk.ComboBoxText()
        for cid, key in self.CHARSET_ITEMS:
            self.combo_src.append(cid, tr(self.lang, key))
        self.combo_src.set_active_id("tcvn3")
        self.combo_src.set_hexpand(True)

        btn_swap = Gtk.Button(label=tr(self.lang, "conv_swap_btn"))
        btn_swap.connect("clicked", self._on_swap_clicked)

        lbl_dst = Gtk.Label(label=tr(self.lang, "conv_dst_label"), xalign=0)
        self.combo_dst = Gtk.ComboBoxText()
        for cid, key in self.DST_CHARSET_ITEMS:
            self.combo_dst.append(cid, tr(self.lang, key))
        self.combo_dst.set_active_id("unicode")
        self.combo_dst.set_hexpand(True)

        lbl_case = Gtk.Label(label=tr(self.lang, "conv_case_label"), xalign=0)
        self.combo_case = Gtk.ComboBoxText()
        for cid, key in self.CASE_ITEMS:
            self.combo_case.append(cid, tr(self.lang, key))
        self.combo_case.set_active_id("none")
        self.combo_case.set_hexpand(True)

        grid.attach(lbl_src, 0, 0, 1, 1)
        grid.attach(self.combo_src, 1, 0, 1, 1)
        grid.attach(btn_swap, 2, 0, 1, 2)
        grid.attach(lbl_dst, 0, 1, 1, 1)
        grid.attach(self.combo_dst, 1, 1, 1, 1)
        grid.attach(lbl_case, 0, 2, 1, 1)
        grid.attach(self.combo_case, 1, 2, 2, 1)
        box.pack_start(grid, False, False, 0)

        # Text Area
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_left_margin(8)
        self.text_view.set_right_margin(8)
        self.text_view.set_top_margin(8)
        self.text_view.set_bottom_margin(8)
        self.text_buffer = self.text_view.get_buffer()
        scroll.add(self.text_view)
        box.pack_start(scroll, True, True, 0)

        # Status Label
        self.lbl_status = Gtk.Label(label=tr(self.lang, "conv_status_ready"), xalign=0)
        self.lbl_status.set_line_wrap(True)
        box.pack_start(self.lbl_status, False, False, 0)

        # Action Buttons
        act_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_clip = Gtk.Button(label=tr(self.lang, "conv_btn_clipboard"))
        btn_clip.get_style_context().add_class("suggested-action")
        btn_clip.connect("clicked", self._on_convert_clipboard)

        btn_text = Gtk.Button(label=tr(self.lang, "conv_btn_text"))
        btn_text.connect("clicked", self._on_convert_textbox)

        btn_copy = Gtk.Button(label=tr(self.lang, "conv_btn_copy"))
        btn_copy.connect("clicked", self._on_copy_result)

        btn_close = Gtk.Button(label=tr(self.lang, "close"))
        btn_close.connect("clicked", lambda w: self.response(Gtk.ResponseType.CLOSE))

        act_box.pack_start(btn_clip, False, False, 0)
        act_box.pack_start(btn_text, False, False, 0)
        act_box.pack_start(btn_copy, False, False, 0)
        act_box.pack_end(btn_close, False, False, 0)
        box.pack_start(act_box, False, False, 0)

        self.show_all()

    def _on_swap_clicked(self, _btn):
        src_id = self.combo_src.get_active_id() or "unicode"
        dst_id = self.combo_dst.get_active_id() or "unicode"
        if dst_id == "ascii":
            dst_id = "unicode"
        self.combo_src.set_active_id(dst_id)
        self.combo_dst.set_active_id(src_id)

    def _get_params(self):
        src_id = self.combo_src.get_active_id() or "unicode"
        dst_id = self.combo_dst.get_active_id() or "unicode"
        case_id = self.combo_case.get_active_id() or "none"
        return src_id, dst_id, case_id

    def _on_convert_clipboard(self, _btn):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        raw_text = clipboard.wait_for_text()
        if not raw_text:
            start, end = self.text_buffer.get_bounds()
            raw_text = self.text_buffer.get_text(start, end, True)
        if not raw_text:
            self.lbl_status.set_text(tr(self.lang, "conv_status_empty"))
            return
        src_id, dst_id, case_id = self._get_params()
        converted = convert_vietnamese_text(raw_text, src_id, dst_id, case_id)
        self.text_buffer.set_text(converted)
        clipboard.set_text(converted, -1)
        clipboard.store()
        self.lbl_status.set_text(
            tr(self.lang, "conv_status_done", n=len(converted), src=src_id.upper(), dst=dst_id.upper())
        )

    def _on_convert_textbox(self, _btn):
        start, end = self.text_buffer.get_bounds()
        raw_text = self.text_buffer.get_text(start, end, True)
        if not raw_text:
            self.lbl_status.set_text(tr(self.lang, "conv_status_empty"))
            return
        src_id, dst_id, case_id = self._get_params()
        converted = convert_vietnamese_text(raw_text, src_id, dst_id, case_id)
        self.text_buffer.set_text(converted)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(converted, -1)
        clipboard.store()
        self.lbl_status.set_text(
            tr(self.lang, "conv_status_done", n=len(converted), src=src_id.upper(), dst=dst_id.upper())
        )

    def _on_copy_result(self, _btn):
        start, end = self.text_buffer.get_bounds()
        text = self.text_buffer.get_text(start, end, True)
        if text:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(text, -1)
            clipboard.store()


class SetupPanel(Gtk.Window):
    ICON_STYLE_CHOICES = [
        ("flag", "us", "ic_flag_us"),
        ("flag", "uk", "ic_flag_uk"),
        ("badge", "us", "ic_badge"),
        ("lotus", "us", "ic_lotus"),
        ("symbolic", "us", "ic_symbolic"),
    ]

    def __init__(self):
        self._initial_cfg = load_config()
        self.cfg = copy.deepcopy(self._initial_cfg)
        self.macros = load_macros()
        self.lang = normalize_lang(self.cfg.get("ui_lang", "vi"))
        self._building_ui = False
        self._macro_search_query = ""

        apply_app_theme(self.cfg.get("theme", "auto"))

        super().__init__(title=tr(self.lang, "settings_title"))
        self.set_default_size(560, 420 if self.cfg.get("compact_mode", True) else 660)
        self.set_position(Gtk.WindowPosition.CENTER)

        icon_p = DistroAdapter.get_status_icon_path(
            active=self.cfg.get("enabled", True),
            icon_style=self.cfg.get("icon_style", "flag"),
            flag_variant=self.cfg.get("flag_variant", "us"),
        )
        pb = load_svg_pixbuf(icon_p, 48)
        if pb is not None:
            self.set_icon(pb)

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
        main_box.set_border_width(14)
        self.root_container.pack_start(main_box, True, True, 0)

        # 1. Header Card with Flat Flag Icon, Status Switch, and UI Language
        header_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_card.get_style_context().add_class("lotus-header-card")

        self.header_icon_img = Gtk.Image()
        header_card.pack_start(self.header_icon_img, False, False, 0)

        env_info = detect_desktop_environment()
        distro_info = DistroAdapter.detect_distro()
        eff_fw = resolve_effective_framework(self.cfg.get("im_framework", "auto")).upper()

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label(
            label="<span size='large' weight='bold'>LotusKey</span>",
            use_markup=True,
            xalign=0,
        )
        lbl_sub = Gtk.Label(
            label=(
                f"<span size='small' alpha='75%'>"
                f"{distro_info['name']} • {env_info['desktop']} ({env_info['session_type'].upper()}) • {eff_fw}"
                f"</span>"
            ),
            use_markup=True,
            xalign=0,
        )
        title_box.pack_start(lbl_title, False, False, 0)
        title_box.pack_start(lbl_sub, False, False, 0)
        header_card.pack_start(title_box, True, True, 0)

        # Vietnamese ON/OFF Switch + Language selector
        right_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        toggle_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toggle_row.set_halign(Gtk.Align.END)

        self.lbl_vn_state = Gtk.Label(xalign=1)
        self.sw_enabled = Gtk.Switch()
        self.sw_enabled.set_active(self.cfg.get("enabled", True))
        self.sw_enabled.set_valign(Gtk.Align.CENTER)
        self.sw_enabled.connect("notify::active", self._on_enabled_switch_toggled)
        toggle_row.pack_start(self.lbl_vn_state, False, False, 0)
        toggle_row.pack_start(self.sw_enabled, False, False, 0)

        lang_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lang_row.set_halign(Gtk.Align.END)
        lbl_lang = Gtk.Label(label=tr(self.lang, "ui_lang_label"), xalign=1)
        self.combo_lang = Gtk.ComboBoxText()
        self.combo_lang.append_text("Tiếng Việt")
        self.combo_lang.append_text("English")
        self.combo_lang.set_active(1 if self.lang == "en" else 0)
        self.combo_lang.connect("changed", self._on_lang_changed)
        lang_row.pack_start(lbl_lang, False, False, 0)
        lang_row.pack_start(self.combo_lang, False, False, 0)

        right_header.pack_start(toggle_row, False, False, 0)
        right_header.pack_start(lang_row, False, False, 0)
        header_card.pack_end(right_header, False, False, 0)
        main_box.pack_start(header_card, False, False, 0)

        # 2. Core Configuration Frame (Always visible in Compact & Advanced modes)
        self._build_core_card(main_box)

        # 3. Compact <-> Advanced Mode Expander Button
        is_compact = bool(self.cfg.get("compact_mode", True))
        self.btn_toggle_compact = Gtk.Button(
            label=tr(self.lang, "btn_expand_adv" if is_compact else "btn_collapse_adv")
        )
        self.btn_toggle_compact.get_style_context().add_class("lotus-expand-btn")
        self.btn_toggle_compact.connect("clicked", self._on_toggle_compact_clicked)
        main_box.pack_start(self.btn_toggle_compact, False, False, 0)

        # 4. Advanced Notebook (4 Tabs)
        self.notebook = Gtk.Notebook()
        self._build_typing_tab()
        self._build_macro_tab()
        self._build_apps_tab()
        self._build_system_tab()
        main_box.pack_start(self.notebook, True, True, 0)

        # 5. Bottom Action Bar: [Clipboard Converter] [Reset] ... [Cancel (Esc)] [Save]
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        btn_conv = Gtk.Button(label=tr(self.lang, "converter_btn"))
        btn_conv.connect("clicked", self._on_open_converter)
        action_bar.pack_start(btn_conv, False, False, 0)

        btn_reset = Gtk.Button(label=tr(self.lang, "reset_default"))
        btn_reset.connect("clicked", self._on_reset_defaults)
        action_bar.pack_start(btn_reset, False, False, 0)

        btn_save = Gtk.Button(label=tr(self.lang, "save"))
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", lambda w: self._on_save_clicked())

        btn_cancel = Gtk.Button(label=tr(self.lang, "cancel"))
        btn_cancel.connect("clicked", lambda w: self._on_cancel_clicked())

        action_bar.pack_end(btn_save, False, False, 0)
        action_bar.pack_end(btn_cancel, False, False, 0)
        main_box.pack_end(action_bar, False, False, 0)

        self._refresh_header_and_icon_previews()
        self.root_container.show_all()
        self.notebook.set_current_page(active_tab)
        self.notebook.set_visible(not is_compact)
        self._building_ui = False

    def _build_core_card(self, parent_box: Gtk.Box):
        frame_main = Gtk.Frame(label=tr(self.lang, "frame_main"))
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_border_width(12)
        frame_main.add(vbox)

        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(12)
        vbox.pack_start(grid, False, False, 0)

        # Row 0: Input Method + Charset
        lbl_im = Gtk.Label(label=tr(self.lang, "lbl_input_method"), xalign=0)
        self.combo_im = Gtk.ComboBoxText()
        for m in (tr(self.lang, "im_telex"), tr(self.lang, "im_vni"), tr(self.lang, "im_telex_vni")):
            self.combo_im.append_text(m)
        curr_im = self.cfg.get("input_method", 0)
        self.combo_im.set_active(curr_im if 0 <= curr_im <= 2 else 0)
        self.combo_im.set_hexpand(True)

        lbl_cs = Gtk.Label(label=tr(self.lang, "lbl_charset"), xalign=0)
        self.combo_cs = Gtk.ComboBoxText()
        charsets = [
            (0, tr(self.lang, "cs_unicode")),
            (31, tr(self.lang, "cs_combining")),
            (27, tr(self.lang, "cs_tcvn3")),
            (34, tr(self.lang, "cs_vni_win")),
        ]
        raw_cs = int(self.cfg.get("charset", 0))
        curr_cs = {9: 31, 5: 27, 12: 34}.get(raw_cs, raw_cs)
        for idx, (cid, name) in enumerate(charsets):
            self.combo_cs.append_text(name)
            if cid == curr_cs:
                self.combo_cs.set_active(idx)
        if self.combo_cs.get_active() < 0:
            self.combo_cs.set_active(0)
        self.combo_cs.set_hexpand(True)

        grid.attach(lbl_im, 0, 0, 1, 1)
        grid.attach(self.combo_im, 1, 0, 1, 1)
        grid.attach(lbl_cs, 2, 0, 1, 1)
        grid.attach(self.combo_cs, 3, 0, 1, 1)

        # Row 1: Toggle Shortcut + Flat Flag / Icon Style (2x2 Dropdown Grid)
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

        lbl_ic = Gtk.Label(label=tr(self.lang, "lbl_icon_style"), xalign=0)
        ic_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.combo_icon_style = Gtk.ComboBoxText()
        curr_style = self.cfg.get("icon_style", "flag")
        curr_flag_var = self.cfg.get("flag_variant", "us")
        active_ic_idx = 0
        for idx, (st_code, fv_code, label_key) in enumerate(self.ICON_STYLE_CHOICES):
            self.combo_icon_style.append_text(tr(self.lang, label_key))
            if st_code == curr_style and (st_code != "flag" or fv_code == curr_flag_var):
                active_ic_idx = idx
        self.combo_icon_style.set_active(active_ic_idx)
        self.combo_icon_style.set_hexpand(True)
        self.combo_icon_style.connect("changed", self._on_icon_style_changed)

        self.preview_on_img = Gtk.Image()
        self.preview_off_img = Gtk.Image()
        lbl_arrow = Gtk.Label(label="↔")
        ic_row.pack_start(self.combo_icon_style, True, True, 0)
        ic_row.pack_start(self.preview_on_img, False, False, 0)
        ic_row.pack_start(lbl_arrow, False, False, 0)
        ic_row.pack_start(self.preview_off_img, False, False, 0)

        grid.attach(lbl_toggle, 0, 1, 1, 1)
        grid.attach(self.combo_toggle, 1, 1, 1, 1)
        grid.attach(lbl_ic, 2, 1, 1, 1)
        grid.attach(ic_row, 3, 1, 1, 1)

        # Row 2: Quick Core Checkboxes (Modern tone & Auto-restore English)
        chk_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.chk_modern = Gtk.CheckButton(label=tr(self.lang, "opt_modern"))
        self.chk_modern.set_active(self.cfg.get("modern_tone_style", True))
        self.chk_bilingual = Gtk.CheckButton(label=tr(self.lang, "opt_bilingual"))
        self.chk_bilingual.set_active(self.cfg.get("auto_correct", True))
        chk_row.pack_start(self.chk_modern, True, True, 0)
        chk_row.pack_start(self.chk_bilingual, True, True, 0)
        vbox.pack_start(chk_row, False, False, 2)

        parent_box.pack_start(frame_main, False, False, 0)

    def _build_typing_tab(self):
        tab_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab_box.set_border_width(10)

        # Output Mode & Word Restore Key Frame (Unified Grid of 2 Dropdowns)
        frame_out = Gtk.Frame(label=tr(self.lang, "frame_output"))
        grid_out = Gtk.Grid()
        grid_out.set_border_width(10)
        grid_out.set_row_spacing(8)
        grid_out.set_column_spacing(12)
        frame_out.add(grid_out)

        lbl_out = Gtk.Label(label=tr(self.lang, "lbl_output_mode"), xalign=0)
        self.combo_output_mode = Gtk.ComboBoxText()
        out_items = [
            ("preedit", tr(self.lang, "out_preedit")),
            ("surrounding", tr(self.lang, "out_surrounding")),
            ("forward", tr(self.lang, "out_forward")),
        ]
        curr_mode = self.cfg.get("output_mode", "preedit")
        for oid, otext in out_items:
            self.combo_output_mode.append(oid, otext)
        self.combo_output_mode.set_active_id(
            curr_mode if curr_mode in ("preedit", "surrounding", "forward") else "preedit"
        )
        self.combo_output_mode.set_hexpand(True)

        lbl_rk = Gtk.Label(label=tr(self.lang, "lbl_restore_key"), xalign=0)
        self.combo_restore = Gtk.ComboBoxText()
        rk_items = [
            ("esc", tr(self.lang, "rk_esc")),
            ("shift_backspace", tr(self.lang, "rk_shift_bs")),
            ("none", tr(self.lang, "rk_none")),
        ]
        curr_rk = self.cfg.get("restore_key", "esc")
        for cid, text in rk_items:
            self.combo_restore.append(cid, text)
        self.combo_restore.set_active_id(curr_rk if curr_rk in ("esc", "shift_backspace", "none") else "esc")
        self.combo_restore.set_hexpand(True)

        grid_out.attach(lbl_out, 0, 0, 1, 1)
        grid_out.attach(self.combo_output_mode, 1, 0, 1, 1)
        grid_out.attach(lbl_rk, 0, 1, 1, 1)
        grid_out.attach(self.combo_restore, 1, 1, 1, 1)

        tab_box.pack_start(frame_out, False, False, 0)

        # Orthography & Typing Rules Frame
        frame_opts = Gtk.Frame(label=tr(self.lang, "frame_options"))
        grid_opts = Gtk.Grid()
        grid_opts.set_border_width(10)
        grid_opts.set_row_spacing(6)
        grid_opts.set_column_spacing(16)
        frame_opts.add(grid_opts)

        self.chk_free = Gtk.CheckButton(label=tr(self.lang, "opt_free_tone"))
        self.chk_free.set_active(self.cfg.get("free_tone_marking", True))

        self.chk_quick_telex = Gtk.CheckButton(label=tr(self.lang, "opt_quick_telex"))
        self.chk_quick_telex.set_active(self.cfg.get("quick_telex", False))

        self.chk_w2u = Gtk.CheckButton(label=tr(self.lang, "opt_w2u"))
        self.chk_w2u.set_active(self.cfg.get("w2u", True))

        self.chk_bracket = Gtk.CheckButton(label=tr(self.lang, "opt_bracket"))
        self.chk_bracket.set_active(self.cfg.get("bracket_transform", True))

        self.chk_underline = Gtk.CheckButton(label=tr(self.lang, "opt_underline"))
        self.chk_underline.set_active(self.cfg.get("preedit_underline", False))

        self.chk_menu_grave = Gtk.CheckButton(label=tr(self.lang, "opt_grave_menu"))
        self.chk_menu_grave.set_active(self.cfg.get("mode_menu_key", "grave") == "grave")

        grid_opts.attach(self.chk_free, 0, 0, 1, 1)
        grid_opts.attach(self.chk_quick_telex, 1, 0, 1, 1)
        grid_opts.attach(self.chk_w2u, 0, 1, 1, 1)
        grid_opts.attach(self.chk_bracket, 1, 1, 1, 1)
        grid_opts.attach(self.chk_underline, 0, 2, 1, 1)
        grid_opts.attach(self.chk_menu_grave, 1, 2, 1, 1)

        tab_box.pack_start(frame_opts, False, False, 0)
        self.notebook.append_page(tab_box, Gtk.Label(label=tr(self.lang, "tab_typing")))

    def _build_macro_tab(self):
        macro_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        macro_box.set_border_width(10)

        # Single-row Macro Toolbar: [☑ Bật gõ tắt] [🔍 Search...] [⚙ Quy tắc gõ tắt ▾] [📁 Nhập / Xuất ▾]
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.chk_macro_enabled = Gtk.CheckButton(label=tr(self.lang, "opt_macro_enable"))
        self.chk_macro_enabled.set_active(self.cfg.get("macro_enabled", True))

        self.entry_macro_search = Gtk.SearchEntry()
        self.entry_macro_search.set_placeholder_text(tr(self.lang, "ph_macro_search"))
        self.entry_macro_search.set_hexpand(True)
        if self._macro_search_query:
            self.entry_macro_search.set_text(self._macro_search_query)
        self.entry_macro_search.connect("search-changed", self._on_macro_search_changed)
        self.entry_macro_search.connect("changed", self._on_macro_search_changed)

        self.chk_macro_cap = Gtk.CheckButton(label=tr(self.lang, "opt_macro_cap"))
        self.chk_macro_cap.set_active(self.cfg.get("auto_capitalize_macro", True))
        self.chk_macro_off = Gtk.CheckButton(label=tr(self.lang, "opt_macro_off"))
        self.chk_macro_off.set_active(self.cfg.get("macro_in_off_mode", False))

        self.btn_macro_rules = Gtk.MenuButton(label=tr(self.lang, "btn_macro_rules"))
        pop_rules = Gtk.Popover()
        box_rules = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box_rules.set_border_width(10)
        box_rules.pack_start(self.chk_macro_cap, False, False, 0)
        box_rules.pack_start(self.chk_macro_off, False, False, 0)
        box_rules.show_all()
        pop_rules.add(box_rules)
        self.btn_macro_rules.set_popover(pop_rules)

        self.btn_macro_io = Gtk.MenuButton(label=tr(self.lang, "btn_macro_io"))
        pop_io = Gtk.Popover()
        box_io = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box_io.set_border_width(8)
        btn_import = Gtk.Button(label=tr(self.lang, "btn_macro_import"))
        btn_import.connect(
            "clicked",
            lambda w: (pop_io.popdown(), pop_io.hide(), self.btn_macro_io.set_active(False), self._on_import_macros(w)),
        )
        btn_export = Gtk.Button(label=tr(self.lang, "btn_macro_export"))
        btn_export.connect(
            "clicked",
            lambda w: (pop_io.popdown(), pop_io.hide(), self.btn_macro_io.set_active(False), self._on_export_macros(w)),
        )
        box_io.pack_start(btn_import, False, False, 0)
        box_io.pack_start(btn_export, False, False, 0)
        box_io.show_all()
        pop_io.add(box_io)
        self.btn_macro_io.set_popover(pop_io)

        top_bar.pack_start(self.chk_macro_enabled, False, False, 0)
        top_bar.pack_start(self.entry_macro_search, True, True, 0)
        top_bar.pack_start(self.btn_macro_rules, False, False, 0)
        top_bar.pack_start(self.btn_macro_io, False, False, 0)
        macro_box.pack_start(top_bar, False, False, 0)

        # Add / Update / Delete row
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.entry_macro_key = Gtk.Entry()
        self.entry_macro_key.set_placeholder_text(tr(self.lang, "ph_macro_key"))
        self.entry_macro_key.set_width_chars(12)

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

        # TreeView with filter model
        self.macro_store = Gtk.ListStore(str, str)
        for item in self.macros:
            self.macro_store.append([item.get("key", ""), item.get("value", "")])

        self.macro_filter = self.macro_store.filter_new()
        self.macro_filter.set_visible_func(self._macro_filter_func)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_min_content_height(150)
        scroll.set_shadow_type(Gtk.ShadowType.IN)

        self.macro_tree = Gtk.TreeView(model=self.macro_filter)
        renderer_key = Gtk.CellRendererText()
        col_key = Gtk.TreeViewColumn(tr(self.lang, "col_macro_key"), renderer_key, text=0)
        col_key.set_min_width(110)
        self.macro_tree.append_column(col_key)

        renderer_val = Gtk.CellRendererText()
        col_val = Gtk.TreeViewColumn(tr(self.lang, "col_macro_val"), renderer_val, text=1)
        col_val.set_expand(True)
        self.macro_tree.append_column(col_val)

        selection = self.macro_tree.get_selection()
        selection.connect("changed", self._on_macro_row_selected)

        scroll.add(self.macro_tree)
        macro_box.pack_start(scroll, True, True, 0)

        self.lbl_tab_macro = Gtk.Label(
            label=f"{tr(self.lang, 'tab_macro')} ({len(self.macro_store)})"
        )
        self.notebook.append_page(macro_box, self.lbl_tab_macro)

    def _build_apps_tab(self):
        app_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        app_box.set_border_width(10)

        frame_smart = Gtk.Frame(label=tr(self.lang, "frame_app_smart"))
        box_smart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_smart.set_border_width(10)
        frame_smart.add(box_smart)

        self.chk_per_app = Gtk.CheckButton(label=tr(self.lang, "opt_per_app"))
        self.chk_per_app.set_active(self.cfg.get("per_app_remember", True))
        self.chk_disable_url = Gtk.CheckButton(label=tr(self.lang, "opt_disable_url"))
        self.chk_disable_url.set_active(self.cfg.get("auto_disable_url_bar", True))
        box_smart.pack_start(self.chk_per_app, False, False, 0)
        box_smart.pack_start(self.chk_disable_url, False, False, 0)
        app_box.pack_start(frame_smart, False, False, 0)

        frame_excl = Gtk.Frame(label=tr(self.lang, "frame_app_exclude"))
        box_excl = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box_excl.set_border_width(10)
        frame_excl.add(box_excl)

        add_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.entry_app_exclude = Gtk.Entry()
        self.entry_app_exclude.set_placeholder_text(tr(self.lang, "ph_app_exclude"))
        self.entry_app_exclude.set_hexpand(True)
        self.entry_app_exclude.connect("activate", lambda w: self._on_add_excluded_app())

        btn_add_app = Gtk.Button(label=tr(self.lang, "btn_app_add"))
        btn_add_app.connect("clicked", lambda w: self._on_add_excluded_app())

        btn_del_app = Gtk.Button(label=tr(self.lang, "btn_app_del"))
        btn_del_app.connect("clicked", lambda w: self._on_del_excluded_app())

        self.btn_app_presets = Gtk.MenuButton(label=tr(self.lang, "btn_app_presets"))
        pop_presets = Gtk.Popover()
        box_presets = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box_presets.set_border_width(8)

        preset_defs = [
            ("btn_app_preset_term", ["kitty", "Alacritty", "wezterm", "foot", "gnome-terminal-server", "konsole"]),
            ("btn_app_preset_ide", ["code", "codium", "cursor", "jetbrains-idea", "nvim-qt"]),
            ("btn_app_preset_games", ["steam", "lutris", "heroic", "prismlauncher"]),
            ("btn_app_preset_pass", ["keepassxc", "bitwarden", "1password"]),
        ]
        for label_key, app_list in preset_defs:
            btn_p = Gtk.Button(label=tr(self.lang, label_key))
            btn_p.connect(
                "clicked",
                lambda w, apps=app_list: (
                    pop_presets.popdown(),
                    pop_presets.hide(),
                    self.btn_app_presets.set_active(False),
                    self._add_app_presets(apps),
                ),
            )
            box_presets.pack_start(btn_p, False, False, 0)

        box_presets.show_all()
        pop_presets.add(box_presets)
        self.btn_app_presets.set_popover(pop_presets)

        add_row.pack_start(self.entry_app_exclude, True, True, 0)
        add_row.pack_start(btn_add_app, False, False, 0)
        add_row.pack_start(btn_del_app, False, False, 0)
        add_row.pack_start(self.btn_app_presets, False, False, 0)
        box_excl.pack_start(add_row, False, False, 0)

        self.excl_store = Gtk.ListStore(str)
        for app_name in self.cfg.get("excluded_apps", DEFAULT_EXCLUDED_APPS):
            if app_name:
                self.excl_store.append([str(app_name)])

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_min_content_height(130)
        scroll.set_shadow_type(Gtk.ShadowType.IN)

        self.excl_tree = Gtk.TreeView(model=self.excl_store)
        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("WM_CLASS / Process", renderer, text=0)
        col.set_expand(True)
        self.excl_tree.append_column(col)
        scroll.add(self.excl_tree)
        box_excl.pack_start(scroll, True, True, 0)

        app_box.pack_start(frame_excl, True, True, 0)
        self.notebook.append_page(app_box, Gtk.Label(label=tr(self.lang, "tab_apps")))

    def _build_system_tab(self):
        sys_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sys_box.set_border_width(10)

        # System & Startup Frame
        frame_sys = Gtk.Frame(label=tr(self.lang, "frame_system"))
        grid_sys = Gtk.Grid()
        grid_sys.set_border_width(10)
        grid_sys.set_row_spacing(8)
        grid_sys.set_column_spacing(12)
        frame_sys.add(grid_sys)

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

        self.chk_autostart = Gtk.CheckButton(label=tr(self.lang, "opt_autostart"))
        self.chk_autostart.set_active(self.cfg.get("autostart", True))

        btn_sync = Gtk.Button(label=tr(self.lang, "btn_sync_now"))
        btn_sync.connect("clicked", self._on_sync_now_clicked)

        grid_sys.attach(lbl_fw, 0, 0, 1, 1)
        grid_sys.attach(self.combo_fw, 1, 0, 1, 1)
        grid_sys.attach(self.chk_autostart, 0, 1, 2, 1)
        grid_sys.attach(btn_sync, 0, 2, 2, 1)
        sys_box.pack_start(frame_sys, False, False, 0)

        # Appearance Frame
        frame_app = Gtk.Frame(label=tr(self.lang, "frame_appearance"))
        grid_app = Gtk.Grid()
        grid_app.set_border_width(10)
        grid_app.set_row_spacing(8)
        grid_app.set_column_spacing(12)
        frame_app.add(grid_app)

        lbl_theme = Gtk.Label(label=tr(self.lang, "lbl_theme"), xalign=0)
        self.combo_theme = Gtk.ComboBoxText()
        themes = [
            ("auto", tr(self.lang, "theme_auto")),
            ("dark", tr(self.lang, "theme_dark")),
            ("light", tr(self.lang, "theme_light")),
        ]
        curr_theme = self.cfg.get("theme", "auto")
        for tid, tname in themes:
            self.combo_theme.append(tid, tname)
        self.combo_theme.set_active_id(curr_theme if curr_theme in ("auto", "dark", "light") else "auto")
        self.combo_theme.set_hexpand(True)
        self.combo_theme.connect("changed", self._on_theme_changed)

        grid_app.attach(lbl_theme, 0, 0, 1, 1)
        grid_app.attach(self.combo_theme, 1, 0, 1, 1)
        sys_box.pack_start(frame_app, False, False, 0)

        self.notebook.append_page(sys_box, Gtk.Label(label=tr(self.lang, "tab_system")))

    def _get_selected_icon_style_and_variant(self):
        idx = self.combo_icon_style.get_active() if hasattr(self, "combo_icon_style") else 0
        if 0 <= idx < len(self.ICON_STYLE_CHOICES):
            return self.ICON_STYLE_CHOICES[idx][0], self.ICON_STYLE_CHOICES[idx][1]
        return "flag", "us"

    def _refresh_header_and_icon_previews(self):
        is_enabled = self.sw_enabled.get_active() if hasattr(self, "sw_enabled") else self.cfg.get("enabled", True)
        icon_style, flag_var = self._get_selected_icon_style_and_variant()

        # Update status text
        if hasattr(self, "lbl_vn_state"):
            ctx = self.lbl_vn_state.get_style_context()
            ctx.remove_class("lotus-status-on")
            ctx.remove_class("lotus-status-off")
            ctx.add_class("lotus-status-on" if is_enabled else "lotus-status-off")
            self.lbl_vn_state.set_text(tr(self.lang, "vn_status_on" if is_enabled else "vn_status_off"))

        # Update header main icon (40x40)
        if hasattr(self, "header_icon_img"):
            hdr_path = DistroAdapter.get_status_icon_path(
                active=is_enabled, icon_style=icon_style, flag_variant=flag_var
            )
            pb_hdr = load_svg_pixbuf(hdr_path, 40)
            if pb_hdr is not None:
                self.header_icon_img.set_from_pixbuf(pb_hdr)

        # Update small ON/OFF preview icons next to combo_icon_style (24x24)
        if hasattr(self, "preview_on_img") and hasattr(self, "preview_off_img"):
            on_path = DistroAdapter.get_status_icon_path(
                active=True, icon_style=icon_style, flag_variant=flag_var
            )
            off_path = DistroAdapter.get_status_icon_path(
                active=False, icon_style=icon_style, flag_variant=flag_var
            )
            pb_on = load_svg_pixbuf(on_path, 24)
            pb_off = load_svg_pixbuf(off_path, 24)
            if pb_on is not None:
                self.preview_on_img.set_from_pixbuf(pb_on)
            if pb_off is not None:
                self.preview_off_img.set_from_pixbuf(pb_off)

    def _on_enabled_switch_toggled(self, switch, _gparam):
        if self._building_ui:
            return
        self.cfg["enabled"] = switch.get_active()
        self._refresh_header_and_icon_previews()

    def _on_icon_style_changed(self, _combo):
        if self._building_ui:
            return
        st, fv = self._get_selected_icon_style_and_variant()
        self.cfg["icon_style"] = st
        self.cfg["flag_variant"] = fv
        self._refresh_header_and_icon_previews()

    def _on_theme_changed(self, combo):
        if self._building_ui:
            return
        theme_id = combo.get_active_id() or "auto"
        self.cfg["theme"] = theme_id
        apply_app_theme(theme_id)

    def _on_toggle_compact_clicked(self, _btn):
        if self._building_ui:
            return
        is_compact = not bool(self.cfg.get("compact_mode", True))
        self.cfg["compact_mode"] = is_compact
        self.btn_toggle_compact.set_label(
            tr(self.lang, "btn_expand_adv" if is_compact else "btn_collapse_adv")
        )
        self.notebook.set_visible(not is_compact)
        width, _ = self.get_size()
        self.resize(max(width, 560), 360 if is_compact else 660)

    def _on_lang_changed(self, combo):
        if self._building_ui:
            return
        curr_tab = self.notebook.get_current_page() if hasattr(self, "notebook") else 0
        self._collect_data()
        self.lang = "en" if combo.get_active() == 1 else "vi"
        self.cfg["ui_lang"] = self.lang
        self._rebuild_ui(active_tab=curr_tab)

    # Macro Filter & Actions
    def _macro_filter_func(self, model, treeiter, _data=None):
        q = self._macro_search_query
        if not q:
            return True
        k = (model[treeiter][0] or "").lower()
        v = (model[treeiter][1] or "").lower()
        return (q in k) or (q in v)

    def _on_macro_search_changed(self, search_entry):
        self._macro_search_query = search_entry.get_text().strip().lower()
        self.macro_filter.refilter()

    def _on_macro_row_selected(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            self.entry_macro_key.set_text(model[treeiter][0])
            self.entry_macro_val.set_text(model[treeiter][1])

    def _refresh_macro_tab_label(self):
        if hasattr(self, "lbl_tab_macro") and hasattr(self, "macro_store"):
            self.lbl_tab_macro.set_text(
                f"{tr(self.lang, 'tab_macro')} ({len(self.macro_store)})"
            )

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
                self._refresh_macro_tab_label()
                return
        self.macro_store.append([k, v])
        self.entry_macro_key.set_text("")
        self.entry_macro_val.set_text("")
        self._refresh_macro_tab_label()

    def _on_delete_macro(self):
        selection = self.macro_tree.get_selection()
        filter_model, filter_iter = selection.get_selected()
        if filter_iter is not None:
            child_iter = filter_model.convert_iter_to_child_iter(filter_iter)
            self.macro_store.remove(child_iter)
            self.entry_macro_key.set_text("")
            self.entry_macro_val.set_text("")
            self._refresh_macro_tab_label()

    def _on_import_macros(self, _btn):
        dlg = Gtk.FileChooserDialog(
            title=tr(self.lang, "btn_macro_import"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dlg.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        flt = Gtk.FileFilter()
        flt.set_name("Macro files (*.txt, *.json, *.conf)")
        flt.add_pattern("*.txt")
        flt.add_pattern("*.json")
        flt.add_pattern("*.conf")
        dlg.add_filter(flt)
        if dlg.run() == Gtk.ResponseType.OK:
            filepath = dlg.get_filename()
            curr_list = [{"key": r[0], "value": r[1]} for r in self.macro_store]
            merged = import_macros_from_file(filepath, curr_list)
            self.macro_store.clear()
            for item in merged:
                self.macro_store.append([item["key"], item["value"]])
            self._refresh_macro_tab_label()
        dlg.destroy()

    def _on_export_macros(self, _btn):
        dlg = Gtk.FileChooserDialog(
            title=tr(self.lang, "btn_macro_export"),
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dlg.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
        )
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_name("lotuskey-macros.txt")
        if dlg.run() == Gtk.ResponseType.OK:
            filepath = dlg.get_filename()
            curr_list = [{"key": r[0], "value": r[1]} for r in self.macro_store]
            export_macros_to_file(filepath, curr_list)
        dlg.destroy()

    # Excluded Apps Actions
    def _on_add_excluded_app(self):
        name = self.entry_app_exclude.get_text().strip()
        if not name:
            return
        for row in self.excl_store:
            if row[0].lower() == name.lower():
                self.entry_app_exclude.set_text("")
                return
        self.excl_store.append([name])
        self.entry_app_exclude.set_text("")

    def _on_del_excluded_app(self):
        selection = self.excl_tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            model.remove(treeiter)

    def _add_app_presets(self, names):
        existing = {row[0].lower() for row in self.excl_store}
        for n in names:
            if n.lower() not in existing:
                self.excl_store.append([n])
                existing.add(n.lower())

    def _on_sync_now_clicked(self, _btn):
        self._collect_data()
        eff = apply_framework_config(self.cfg, self.macros, switch_daemon=True)
        try:
            subprocess.Popen(
                [
                    "notify-send", "-t", "1500",
                    "-i", DistroAdapter.get_status_icon_path(active=True, icon_style=self.cfg.get("icon_style", "flag")),
                    "LotusKey",
                    tr(self.lang, "sync_ok_msg", fw=eff.upper()),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def _on_open_converter(self, _btn):
        dlg = CharsetConverterDialog(parent=self, lang=self.lang)
        dlg.run()
        dlg.destroy()

    def _on_reset_defaults(self, _btn):
        curr_tab = self.notebook.get_current_page() if hasattr(self, "notebook") else 0
        self.cfg = copy.deepcopy(DEFAULT_CONFIG)
        self.cfg["ui_lang"] = self.lang
        self._macro_search_query = ""
        apply_app_theme(self.cfg.get("theme", "auto"))
        self._rebuild_ui(active_tab=curr_tab)

    def _collect_data(self):
        self.cfg["ui_lang"] = self.lang
        self.cfg["enabled"] = self.sw_enabled.get_active()

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

        st, fv = self._get_selected_icon_style_and_variant()
        self.cfg["icon_style"] = st
        self.cfg["flag_variant"] = fv

        self.cfg["output_mode"] = self.combo_output_mode.get_active_id() or "preedit"
        self.cfg["restore_key"] = self.combo_restore.get_active_id() or "esc"
        self.cfg["theme"] = self.combo_theme.get_active_id() or "auto"

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
        self.cfg["auto_capitalize_macro"] = self.chk_macro_cap.get_active()
        self.cfg["macro_in_off_mode"] = self.chk_macro_off.get_active()

        self.cfg["per_app_remember"] = self.chk_per_app.get_active()
        self.cfg["auto_disable_url_bar"] = self.chk_disable_url.get_active()
        self.cfg["excluded_apps"] = [row[0] for row in self.excl_store if row[0]]

        self.macros = [{"key": row[0], "value": row[1]} for row in self.macro_store]

    def _apply_and_save(self, notify: bool = True):
        self._collect_data()
        DistroAdapter.install_user_icons(BASE_DIR)
        save_macros(self.macros)
        save_config(self.cfg)

        effective_fw = apply_framework_config(self.cfg, self.macros, switch_daemon=True)

        if notify:
            im_idx = self.cfg.get("input_method", 0)
            im_label = "VNI" if im_idx == 1 else ("Telex+VNI" if im_idx == 2 else "Telex")
            tg_label = self.cfg.get("toggle_key", "Both")
            body = tr(self.lang, "notify_saved_body", fw=effective_fw.upper(), im=im_label, tg=tg_label)
            icon_p = DistroAdapter.get_status_icon_path(
                active=self.cfg.get("enabled", True),
                icon_style=self.cfg.get("icon_style", "flag"),
                flag_variant=self.cfg.get("flag_variant", "us"),
            )
            try:
                subprocess.Popen(
                    [
                        "notify-send",
                        "-t",
                        "1600",
                        "-h",
                        "string:x-canonical-private-synchronous:lotus-config",
                        "-i",
                        icon_p,
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

    def _on_cancel_clicked(self):
        apply_app_theme(self._initial_cfg.get("theme", "auto"))
        self.close()

    def _on_delete_event(self, _widget, _event):
        apply_app_theme(self._initial_cfg.get("theme", "auto"))
        return False

    def _on_key_press(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            for menu_btn in (
                getattr(self, "btn_macro_rules", None),
                getattr(self, "btn_macro_io", None),
                getattr(self, "btn_app_presets", None),
            ):
                if menu_btn is not None:
                    pop = menu_btn.get_popover()
                    if pop is not None and pop.get_visible():
                        pop.popdown()
                        pop.hide()
                        menu_btn.set_active(False)
                        return True
            for combo in (
                getattr(self, "combo_lang", None),
                getattr(self, "combo_im", None),
                getattr(self, "combo_cs", None),
                getattr(self, "combo_toggle", None),
                getattr(self, "combo_icon_style", None),
                getattr(self, "combo_output_mode", None),
                getattr(self, "combo_restore", None),
                getattr(self, "combo_fw", None),
                getattr(self, "combo_theme", None),
            ):
                if combo is not None and combo.get_property("popup-shown"):
                    combo.popdown()
                    return True
            self._on_cancel_clicked()
            return True
        if (
            event.keyval == Gdk.KEY_F6
            and (event.state & Gdk.ModifierType.CONTROL_MASK)
            and (event.state & Gdk.ModifierType.SHIFT_MASK)
        ):
            self._on_open_converter(None)
            return True
        return False


def main():
    if "--converter" in sys.argv:
        cfg = load_config()
        apply_app_theme(cfg.get("theme", "auto"))
        dlg = CharsetConverterDialog(parent=None, lang=cfg.get("ui_lang", "vi"))
        dlg.run()
        dlg.destroy()
        return

    win = SetupPanel()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    if win.cfg.get("compact_mode", True):
        win.notebook.set_visible(False)
    win.present()
    Gtk.main()


if __name__ == "__main__":
    main()
