#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Localization Strings (Vietnamese & English)
Concise, standard terminology for input method settings and dialogs.
"""

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "vi": {
        # Common
        "app_name": "LotusKey",
        "settings_title": "Cấu hình LotusKey",
        "quick_menu_title": "Bảng chọn nhanh LotusKey",
        "wizard_title": "Cài đặt LotusKey",
        "ui_lang_label": "Ngôn ngữ:",
        "save": "Lưu",
        "close": "Đóng",
        "cancel": "Hủy",
        "back": "Quay lại",
        "next": "Tiếp tục",
        "install": "Cài đặt",
        "installing": "Đang cài đặt...",
        "finish": "Hoàn tất",
        "rescan": "Kiểm tra lại",
        "installed_tag": "Đã cài",
        "not_installed_tag": "Chưa cài",
        "active_tag": "Đang dùng",

        # Tabs
        "tab_general": "Cài đặt chung",
        "tab_macro": "Gõ tắt",

        # Setup Panel - Frame 1: Input Method
        "frame_main": " Bộ gõ ",
        "lbl_framework": "Hệ thống đích:",
        "fw_auto": "Tự động",
        "fw_ibus": "IBus",
        "fw_fcitx5": "Fcitx5",
        "fw_fcitx": "Fcitx4",
        "fw_uinput": "UInput (Kernel)",
        "lbl_charset": "Bảng mã:",
        "cs_unicode": "Unicode dựng sẵn",
        "cs_combining": "Unicode tổ hợp",
        "cs_tcvn3": "TCVN3 (ABC)",
        "cs_vni_win": "VNI Windows",
        "lbl_input_method": "Kiểu gõ:",
        "im_telex": "Telex",
        "im_vni": "VNI",
        "im_telex_vni": "Telex + VNI",
        "lbl_toggle_key": "Phím chuyển:",
        "tg_both": "Ctrl + Shift và Alt + Z",
        "tg_ctrl_shift": "Ctrl + Shift",
        "tg_alt_z": "Alt + Z",
        "tg_shift_space": "Shift + Space",
        "tg_none": "Tắt",

        # Setup Panel - Frame 2: Output Mode
        "frame_output": " Phương thức xuất chữ ",
        "out_preedit": "Pre-edit (Mặc định, ổn định nhất)",
        "out_surrounding": "Surrounding Text (Thay thế trực tiếp)",
        "out_forward": "Forward Backspace (Dành cho X11 / Terminal cũ)",

        # Setup Panel - Frame 3: Typing Options
        "frame_options": " Tùy chọn gõ ",
        "opt_bilingual": "Tự khôi phục từ tiếng Anh",
        "opt_modern": "Đặt dấu kiểu mới (oà, uý)",
        "opt_free_tone": "Bỏ dấu tự do",
        "opt_quick_telex": "Gõ tắt phụ âm (cc=ch, gg=gi, nn=ng)",
        "opt_w2u": "Đổi W thành Ư ở đầu từ",
        "opt_bracket": "Gõ [ thành ơ, ] thành ư",
        "opt_underline": "Gạch chân từ đang gõ",
        "opt_grave_menu": "Phím ` mở bảng chọn nhanh (gõ `` để nhập dấu `)",
        "opt_autostart": "Khởi động cùng hệ thống",

        # Setup Panel - Macro Tab
        "opt_macro_enable": "Bật gõ tắt (tự khớp chữ hoa/thường)",
        "ph_macro_key": "Viết tắt (vd: vn)",
        "ph_macro_val": "Thay thế bằng (vd: Việt Nam)",
        "btn_macro_add": "Thêm / Sửa",
        "btn_macro_del": "Xóa",
        "col_macro_key": "Viết tắt",
        "col_macro_val": "Thay thế bằng",

        # Notifications
        "notify_saved_body": "Đã lưu cấu hình ({fw})\nKiểu gõ: {im} • Phím chuyển: {tg}",

        # Quick Menu
        "qm_enable_vn": "Gõ tiếng Việt",
        "qm_input_method": "Kiểu gõ",
        "qm_framework": "Hệ thống đích",
        "qm_output_mode": "Xuất chữ",
        "qm_options": "Tùy chọn",
        "qm_hint": "Nhấn ` mở menu • Nhấn `` gõ dấu ` • Ctrl+Shift đổi ngôn ngữ • Esc đóng",

        # Setup Wizard
        "wiz_step_1": "1. Giới thiệu",
        "wiz_step_2": "2. Kiểm tra hệ thống",
        "wiz_step_3": "3. Cài đặt",
        "wiz_step_4": "4. Hoàn tất",
        "wiz_welcome_head": "Trình cài đặt LotusKey",
        "wiz_welcome_desc": "Thiết lập bộ gõ tiếng Việt cho Linux (Wayland và X11).",
        "wiz_welcome_body": (
            "<b>LotusKey</b> hỗ trợ gõ tiếng Việt qua IBus, Fcitx5 và UInput:\n\n"
            "• Kiểu gõ: Telex, VNI, Telex + VNI.\n"
            "• Bảng mã: Unicode dựng sẵn, Unicode tổ hợp, TCVN3, VNI Windows.\n"
            "• Tự động khôi phục từ tiếng Anh và hỗ trợ gõ tắt.\n"
            "• Tương thích với GNOME, KDE Plasma, Hyprland, Sway, XFCE, Cinnamon."
        ),
        "wiz_chk_autostart": "Khởi động cùng hệ thống",
        "wiz_chk_open_cfg": "Mở cửa sổ cấu hình sau khi cài đặt",
        "wiz_scan_head": "Kiểm tra môi trường hệ thống",
        "wiz_scan_desc": "Trạng thái các thành phần cần thiết trên máy:",
        "wiz_inst_head": "Đang cài đặt LotusKey",
        "wiz_inst_prep": "Đang chuẩn bị...",
        "wiz_inst_running": "Đang thực hiện ({i}/{total}): {name}...",
        "wiz_inst_fail": "Cài đặt thất bại. Xem chi tiết bên dưới.",
        "wiz_inst_done": "Đã hoàn tất cài đặt.",
        "wiz_log_label": "Nhật ký chi tiết",
        "wiz_s1": "Khởi tạo thư mục cấu hình và biểu tượng",
        "wiz_s2": "Biên dịch bộ gõ C (IBus và UInput)",
        "wiz_s3": "Đăng ký thành phần bộ gõ với hệ thống",
        "wiz_s4": "Tạo liên kết lệnh và lối tắt ứng dụng",
        "wiz_s5": "Thiết lập khởi động cùng hệ thống",
        "wiz_s6": "Kích hoạt bộ gõ",
        "wiz_fin_head": "Cài đặt hoàn tất",
        "wiz_fin_desc": "LotusKey đã sẵn sàng sử dụng.",
        "wiz_fin_summary": (
            "<b>Thông tin mặc định:</b>\n"
            "• Kiểu gõ: <b>Telex</b>\n"
            "• Phím chuyển ngôn ngữ: <b>Ctrl + Shift</b> hoặc <b>Alt + Z</b>\n"
            "• Bảng chọn nhanh: Phím <b>`</b>\n"
            "• Lệnh mở cấu hình: <tt>lotuskey-setup</tt>"
        ),
    },
    "en": {
        # Common
        "app_name": "LotusKey",
        "settings_title": "LotusKey Settings",
        "quick_menu_title": "LotusKey Quick Menu",
        "wizard_title": "LotusKey Installer",
        "ui_lang_label": "Language:",
        "save": "Save",
        "close": "Close",
        "cancel": "Cancel",
        "back": "Back",
        "next": "Next",
        "install": "Install",
        "installing": "Installing...",
        "finish": "Finish",
        "rescan": "Rescan",
        "installed_tag": "Installed",
        "not_installed_tag": "Not installed",
        "active_tag": "Active",

        # Tabs
        "tab_general": "General",
        "tab_macro": "Macros",

        # Setup Panel - Frame 1: Input Method
        "frame_main": " Input Method ",
        "lbl_framework": "Backend:",
        "fw_auto": "Auto",
        "fw_ibus": "IBus",
        "fw_fcitx5": "Fcitx5",
        "fw_fcitx": "Fcitx4",
        "fw_uinput": "UInput (Kernel)",
        "lbl_charset": "Charset:",
        "cs_unicode": "Unicode (Precomposed)",
        "cs_combining": "Unicode (Combining)",
        "cs_tcvn3": "TCVN3 (ABC)",
        "cs_vni_win": "VNI Windows",
        "lbl_input_method": "Input method:",
        "im_telex": "Telex",
        "im_vni": "VNI",
        "im_telex_vni": "Telex + VNI",
        "lbl_toggle_key": "Toggle shortcut:",
        "tg_both": "Ctrl + Shift and Alt + Z",
        "tg_ctrl_shift": "Ctrl + Shift",
        "tg_alt_z": "Alt + Z",
        "tg_shift_space": "Shift + Space",
        "tg_none": "Disabled",

        # Setup Panel - Frame 2: Output Mode
        "frame_output": " Output Mode ",
        "out_preedit": "Pre-edit (Default, most reliable)",
        "out_surrounding": "Surrounding Text (Direct replacement)",
        "out_forward": "Forward Backspace (Legacy X11 / Terminals)",

        # Setup Panel - Frame 3: Typing Options
        "frame_options": " Typing Options ",
        "opt_bilingual": "Auto-restore English words",
        "opt_modern": "Modern tone placement (oà, uý)",
        "opt_free_tone": "Free tone marking",
        "opt_quick_telex": "Consonant shorthand (cc=ch, gg=gi, nn=ng)",
        "opt_w2u": "Convert initial W to Ư",
        "opt_bracket": "Map [ to ơ and ] to ư",
        "opt_underline": "Underline pre-edit text",
        "opt_grave_menu": "Press ` for Quick Menu (double-tap `` for literal `)",
        "opt_autostart": "Start automatically on login",

        # Setup Panel - Macro Tab
        "opt_macro_enable": "Enable macro expansion (case-aware)",
        "ph_macro_key": "Shortcut (e.g. vn)",
        "ph_macro_val": "Expansion (e.g. Việt Nam)",
        "btn_macro_add": "Add / Update",
        "btn_macro_del": "Delete",
        "col_macro_key": "Shortcut",
        "col_macro_val": "Expansion",

        # Notifications
        "notify_saved_body": "Settings saved ({fw})\nMethod: {im} • Shortcut: {tg}",

        # Quick Menu
        "qm_enable_vn": "Vietnamese input",
        "qm_input_method": "Input method",
        "qm_framework": "Backend",
        "qm_output_mode": "Output mode",
        "qm_options": "Options",
        "qm_hint": "` Quick Menu • `` literal ` • Ctrl+Shift toggle • Esc close",

        # Setup Wizard
        "wiz_step_1": "1. Overview",
        "wiz_step_2": "2. System Check",
        "wiz_step_3": "3. Install",
        "wiz_step_4": "4. Finish",
        "wiz_welcome_head": "LotusKey Installer",
        "wiz_welcome_desc": "Configure Vietnamese input method for Linux (Wayland and X11).",
        "wiz_welcome_body": (
            "<b>LotusKey</b> supports Vietnamese input across IBus, Fcitx5, and UInput:\n\n"
            "• Input methods: Telex, VNI, Telex + VNI.\n"
            "• Charsets: Unicode NFC, Unicode NFD, TCVN3, VNI Windows.\n"
            "• English word auto-restore and macro expansion.\n"
            "• Works on GNOME, KDE Plasma, Hyprland, Sway, XFCE, and Cinnamon."
        ),
        "wiz_chk_autostart": "Start automatically on login",
        "wiz_chk_open_cfg": "Open settings after installation",
        "wiz_scan_head": "System Environment Check",
        "wiz_scan_desc": "Status of required components:",
        "wiz_inst_head": "Installing LotusKey",
        "wiz_inst_prep": "Preparing...",
        "wiz_inst_running": "Running ({i}/{total}): {name}...",
        "wiz_inst_fail": "Installation failed. See log below.",
        "wiz_inst_done": "Installation completed.",
        "wiz_log_label": "Build & install log",
        "wiz_s1": "Initialize configuration and icons",
        "wiz_s2": "Compile C engines (IBus and UInput)",
        "wiz_s3": "Register input method component",
        "wiz_s4": "Create CLI links and desktop entry",
        "wiz_s5": "Configure login autostart",
        "wiz_s6": "Activate input method",
        "wiz_fin_head": "Installation Complete",
        "wiz_fin_desc": "LotusKey is ready to use.",
        "wiz_fin_summary": (
            "<b>Default configuration:</b>\n"
            "• Input method: <b>Telex</b>\n"
            "• Toggle shortcut: <b>Ctrl + Shift</b> or <b>Alt + Z</b>\n"
            "• Quick Menu key: <b>`</b> (grave)\n"
            "• Settings command: <tt>lotuskey-setup</tt>"
        ),
    },
}


def normalize_lang(lang: str) -> str:
    if lang and str(lang).lower().startswith("en"):
        return "en"
    return "vi"


def tr(lang: str, key: str, **kwargs) -> str:
    code = normalize_lang(lang)
    table = STRINGS.get(code, STRINGS["vi"])
    text = table.get(key, STRINGS["vi"].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text
