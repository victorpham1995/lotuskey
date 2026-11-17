#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Localization Strings (Vietnamese & English) & Unified Theme Engine
Concise, standard terminology for input method settings, quick menu, converter, and installer.
"""

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "vi": {
        # Common
        "app_name": "LotusKey",
        "settings_title": "Cấu hình LotusKey",
        "quick_menu_title": "Bảng chọn nhanh LotusKey",
        "wizard_title": "Cài đặt LotusKey",
        "wiz_title": "Cài đặt LotusKey",
        "wiz_author": "Bộ gõ Tiếng Việt đa nền tảng",
        "ui_lang_label": "Ngôn ngữ:",
        "lang_label": "Ngôn ngữ:",
        "save": "💾 Lưu",
        "close": "Đóng",
        "cancel": "Hủy (Esc)",
        "reset_default": "↺ Mặc định",
        "converter_btn": "🔄 Chuyển mã Clipboard",
        "back": "Quay lại",
        "next": "Tiếp tục",
        "install": "Cài đặt",
        "installing": "Đang cài đặt...",
        "finish": "Hoàn tất",
        "rescan": "Kiểm tra lại",
        "installed_tag": "Đã cài",
        "not_installed_tag": "Chưa cài",
        "active_tag": "Đang dùng",
        "vn_status_on": "Tiếng Việt: BẬT",
        "vn_status_off": "Tiếng Anh: TẮT",

        # Compact / Advanced Mode Toggle
        "btn_expand_adv": "▼ Mở rộng tùy chọn nâng cao (Quy tắc gõ, Gõ tắt, Ứng dụng, Hệ thống)",
        "btn_collapse_adv": "▲ Thu gọn tùy chọn nâng cao",

        # Tabs (Advanced Mode)
        "tab_general": "1. Quy tắc gõ",
        "tab_typing": "1. Quy tắc gõ",
        "tab_macro": "2. Bảng gõ tắt",
        "tab_apps": "3. Ứng dụng",
        "tab_system": "4. Hệ thống & Giao diện",

        # Setup Panel - Basic Card
        "frame_main": " Cấu hình cơ bản ",
        "lbl_framework": "Hệ thống đích:",
        "fw_auto": "Tự động",
        "fw_ibus": "IBus",
        "fw_fcitx5": "Fcitx5",
        "fw_fcitx": "Fcitx4",
        "fw_uinput": "UInput (Kernel)",
        "lbl_charset": "Bảng mã:",
        "cs_unicode": "Unicode dựng sẵn (NFC)",
        "cs_combining": "Unicode tổ hợp (NFD)",
        "cs_tcvn3": "TCVN3 (ABC)",
        "cs_vni_win": "VNI Windows",
        "cs_ascii": "Không dấu (ASCII)",
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
        "lbl_icon_style": "Biểu tượng khay:",
        "ic_flag_us": "Cờ phẳng VN / US (Mặc định)",
        "ic_flag_uk": "Cờ phẳng VN / UK",
        "ic_badge": "Chữ V / E phẳng (UniKey)",
        "ic_lotus": "Hoa sen LotusKey",
        "ic_symbolic": "Đơn sắc (Symbolic)",

        # Setup Panel - Tab 1: Output Mode & Typing Options
        "frame_output": " Phương thức xuất chữ ",
        "lbl_output_mode": "Chế độ xuất chữ:",
        "out_preedit": "Pre-edit (Mặc định, ổn định nhất)",
        "out_surrounding": "Surrounding Text (Thay thế trực tiếp)",
        "out_forward": "Forward Backspace (Dành cho X11 / Terminal cũ)",
        "lbl_restore_key": "Phím khôi phục từ:",
        "rk_esc": "Phím Esc (Khôi phục từ đang gõ về tiếng Anh)",
        "rk_shift_bs": "Shift + Backspace",
        "rk_none": "Tắt",
        "frame_options": " Quy tắc chính tả & Tùy chọn gõ ",
        "opt_bilingual": "Tự khôi phục từ tiếng Anh",
        "opt_modern": "Đặt dấu kiểu mới (oà, uý)",
        "opt_free_tone": "Bỏ dấu tự do (SEN Flex)",
        "opt_quick_telex": "Gõ tắt phụ âm (cc=ch, gg=gi, nn=ng)",
        "opt_w2u": "Đổi W thành Ư ở đầu từ",
        "opt_bracket": "Gõ [ thành ơ, ] thành ư",
        "opt_underline": "Gạch chân từ đang gõ",
        "opt_grave_menu": "Phím ` mở bảng chọn nhanh (gõ `` để nhập dấu `)",
        "opt_autostart": "Khởi động cùng hệ thống",

        # Setup Panel - Tab 2: Macro Tab
        "opt_macro_enable": "Bật gõ tắt (Macro)",
        "opt_macro_cap": "Tự động khớp chữ HOA / thường theo từ gõ tắt",
        "opt_macro_off": "Cho phép gõ tắt cả khi đang tắt Tiếng Việt",
        "btn_macro_rules": "⚙ Quy tắc gõ tắt ▾",
        "btn_macro_io": "📁 Nhập / Xuất ▾",
        "ph_macro_search": "🔍 Tìm kiếm từ viết tắt hoặc nội dung...",
        "ph_macro_key": "Viết tắt (vd: vn)",
        "ph_macro_val": "Thay thế bằng (vd: Việt Nam)",
        "btn_macro_add": "Thêm / Sửa",
        "btn_macro_del": "Xóa",
        "btn_macro_import": "📥 Nhập file...",
        "btn_macro_export": "📤 Xuất file...",
        "col_macro_key": "Viết tắt",
        "col_macro_val": "Thay thế bằng",

        # Setup Panel - Tab 3: Per-App & Exclusion Rules
        "frame_app_smart": " Chuyển trạng thái thông minh ",
        "opt_per_app": "Nhớ trạng thái Tiếng Việt / Tiếng Anh riêng cho từng cửa sổ ứng dụng",
        "opt_disable_url": "Tự động tắt Tiếng Việt trên thanh địa chỉ (URL) và ô mật khẩu",
        "frame_app_exclude": " Danh sách ứng dụng loại trừ (Tự chuyển sang Tiếng Anh) ",
        "ph_app_exclude": "Tên tiến trình hoặc WM_CLASS (vd: kitty, code, steam)",
        "btn_app_add": "Thêm",
        "btn_app_del": "Xóa",
        "btn_app_presets": "➕ Thêm nhóm mẫu ▾",
        "btn_app_preset_term": "+ Terminal (kitty, Alacritty, wezterm, foot, konsole)",
        "btn_app_preset_ide": "+ VS Code / IDE (code, codium, cursor, jetbrains, nvim)",
        "btn_app_preset_games": "+ Games / Steam (steam, lutris, heroic, prismlauncher)",
        "btn_app_preset_pass": "+ Trình quản lý mật khẩu (keepassxc, bitwarden, 1password)",

        # Setup Panel - Tab 4: System & Appearance
        "frame_system": " Hệ thống & Khởi động ",
        "frame_appearance": " Giao diện & Hiển thị ",
        "lbl_theme": "Giao diện hộp thoại:",
        "theme_auto": "Theo hệ thống (System Auto)",
        "theme_dark": "Lotus Dark (Tối)",
        "theme_light": "Lotus Light (Sáng)",
        "btn_sync_now": "⚡ Kiểm tra & Đồng bộ lại bộ gõ ngay",
        "sync_ok_msg": "Đã đồng bộ thành công với backend: {fw}",

        # Clipboard Charset Converter Dialog
        "conv_title": "Công cụ Chuyển mã Clipboard & Văn bản",
        "conv_src_label": "Bảng mã nguồn:",
        "conv_dst_label": "Bảng mã đích:",
        "conv_swap_btn": "⇄ Đảo chiều",
        "conv_case_label": "Chuyển chữ hoa/thường:",
        "case_none": "Giữ nguyên",
        "case_upper": "CHỮ HOA (UPPERCASE)",
        "case_lower": "chữ thường (lowercase)",
        "case_title": "Hoa Đầu Từ (Title Case)",
        "conv_placeholder": "Nhập hoặc dán văn bản cần chuyển mã tại đây...",
        "conv_btn_clipboard": "📋 Chuyển mã Clipboard ngay",
        "conv_btn_text": "⚡ Chuyển đổi ô văn bản",
        "conv_btn_copy": "📑 Sao chép kết quả",
        "conv_status_ready": "Sẵn sàng chuyển đổi 2 chiều (Unicode ↔ TCVN3 ↔ VNI ↔ Tổ hợp ↔ Không dấu).",
        "conv_status_done": "✔ Đã chuyển đổi ({n} ký tự) từ {src} → {dst} và cập nhật Clipboard!",
        "conv_status_empty": "⚠ Clipboard hiện đang trống.",

        # Notifications
        "notify_saved_body": "Đã lưu cấu hình ({fw})\nKiểu gõ: {im} • Phím chuyển: {tg}",

        # Quick Menu
        "qm_enable_vn": "Gõ tiếng Việt",
        "qm_input_method": "Kiểu gõ",
        "qm_charset": "Bảng mã",
        "qm_framework": "Hệ thống",
        "qm_output_mode": "Xuất chữ",
        "qm_icon_style": "Biểu tượng",
        "qm_options": "Tùy chọn nhanh",
        "qm_cs_unicode": "Unicode (NFC)",
        "qm_cs_combining": "Tổ hợp (NFD)",
        "qm_ic_flag_us": "Cờ VN / US",
        "qm_ic_flag_uk": "Cờ VN / UK",
        "qm_ic_badge": "Chữ V / E",
        "qm_ic_lotus": "Hoa sen",
        "qm_ic_symbolic": "Đơn sắc",
        "qm_open_setup": "⚙ Cài đặt đầy đủ",
        "qm_open_conv": "🔄 Chuyển mã",
        "qm_hint": "Nhấn ` mở menu • Nhấn `` gõ dấu ` • Ctrl+Shift đổi ngôn ngữ • Esc đóng",

        # Setup Wizard (including all 22 previously missing keys)
        "scan_distro": "Bản phân phối Linux",
        "scan_session": "Phiên đồ họa (Display)",
        "scan_im": "Khung bộ gõ (IM Backend)",
        "scan_gcc": "Trình biên dịch C (GCC/Clang)",
        "scan_installed": "Đã cài đặt",
        "scan_missing": "Chưa cài đặt (Dùng bản dựng sẵn)",
        "scan_core": "Nhân xử lý LotusKey C-ABI",
        "scan_abi_ok": "Tương thích hoàn toàn (OK)",
        "scan_gtk": "Thư viện giao diện GTK3",
        "scan_ready": "Sẵn sàng",
        "wiz_step_1": "1. Giới thiệu",
        "wiz_step_2": "2. Kiểm tra hệ thống",
        "wiz_step_3": "3. Cài đặt",
        "wiz_step_4": "4. Hoàn tất",
        "wiz_welcome_head": "Trình cài đặt LotusKey",
        "wiz_welcome_desc": "Thiết lập bộ gõ tiếng Việt cho Linux (Wayland và X11).",
        "wiz_welcome_body": (
            "<b>LotusKey</b> hỗ trợ gõ tiếng Việt qua IBus, Fcitx5 và UInput:\n\n"
            "• Kiểu gõ: Telex, VNI, Telex + VNI.\n"
            "• Biểu tượng Cờ phẳng (VN / US / UK), Chữ V/E, Hoa sen, Đơn sắc.\n"
            "• Bảng mã: Unicode dựng sẵn, Unicode tổ hợp, TCVN3, VNI Windows.\n"
            "• Tự động khôi phục từ tiếng Anh (hoặc nhấn Esc) và hỗ trợ gõ tắt.\n"
            "• Tương thích với GNOME, KDE Plasma, Hyprland, Sway, XFCE, Cinnamon."
        ),
        "wiz_chk_autostart": "Khởi động cùng hệ thống",
        "wiz_chk_open_cfg": "Mở cửa sổ cấu hình sau khi cài đặt",
        "wiz_chk_open_now": "Mở bảng cấu hình LotusKey ngay bây giờ",
        "wiz_scan_head": "Kiểm tra môi trường hệ thống",
        "wiz_scan_desc": "Trạng thái các thành phần cần thiết trên máy:",
        "wiz_inst_head": "Đang cài đặt LotusKey",
        "wiz_inst_prep": "Đang chuẩn bị...",
        "wiz_inst_running": "Đang thực hiện ({i}/{total}): {name}...",
        "wiz_inst_fail": "Cài đặt thất bại. Xem nhật ký chi tiết bên dưới.",
        "wiz_inst_done": "Đã hoàn tất cài đặt.",
        "wiz_log_label": "Nhật ký chi tiết",
        "wiz_inst_log": "Nhật ký chi tiết",
        "wiz_s1": "Khởi tạo thư mục cấu hình và bộ biểu tượng cờ phẳng",
        "wiz_s2": "Biên dịch bộ gõ C (IBus và UInput)",
        "wiz_s3": "Đăng ký thành phần bộ gõ với hệ thống",
        "wiz_s4": "Tạo liên kết lệnh và lối tắt ứng dụng",
        "wiz_s5": "Thiết lập khởi động cùng hệ thống (lotuskey-autostart)",
        "wiz_s6": "Kích hoạt và đồng bộ bộ gõ",
        "wiz_fin_head": "Cài đặt hoàn tất",
        "wiz_finish_head": "Cài đặt hoàn tất",
        "wiz_fin_desc": "LotusKey đã sẵn sàng sử dụng.",
        "wiz_finish_desc": "LotusKey đã sẵn sàng sử dụng.",
        "wiz_fin_summary": (
            "<b>Thông tin mặc định:</b>\n"
            "• Kiểu gõ: <b>Telex</b>  •  Biểu tượng: <b>Cờ phẳng VN / US</b>\n"
            "• Phím chuyển ngôn ngữ: <b>Ctrl + Shift</b> hoặc <b>Alt + Z</b>\n"
            "• Phím khôi phục từ về tiếng Anh: <b>Esc</b>\n"
            "• Bảng chọn nhanh: Phím <b>`</b>  •  Cấu hình: <tt>lotuskey-setup</tt>"
        ),
        "wiz_finish_body": (
            "<b>Thông tin mặc định:</b>\n"
            "• Kiểu gõ: <b>Telex</b>  •  Biểu tượng: <b>Cờ phẳng VN / US</b>\n"
            "• Phím chuyển ngôn ngữ: <b>Ctrl + Shift</b> hoặc <b>Alt + Z</b>\n"
            "• Phím khôi phục từ về tiếng Anh: <b>Esc</b>\n"
            "• Bảng chọn nhanh: Phím <b>`</b>  •  Cấu hình: <tt>lotuskey-setup</tt>"
        ),
        "wiz_btn_cancel": "Hủy",
        "wiz_btn_back": "Quay lại",
        "wiz_btn_next": "Tiếp tục",
        "wiz_btn_install": "Cài đặt",
        "wiz_btn_installing": "Đang cài đặt...",
        "wiz_btn_finish": "Hoàn tất",
        "wiz_btn_rescan": "Kiểm tra lại",
    },
    "en": {
        # Common
        "app_name": "LotusKey",
        "settings_title": "LotusKey Settings",
        "quick_menu_title": "LotusKey Quick Menu",
        "wizard_title": "LotusKey Installer",
        "wiz_title": "LotusKey Installer",
        "wiz_author": "Cross-Platform Vietnamese Input Method",
        "ui_lang_label": "Language:",
        "lang_label": "Language:",
        "save": "💾 Save",
        "close": "Close",
        "cancel": "Cancel (Esc)",
        "reset_default": "↺ Reset Defaults",
        "converter_btn": "🔄 Clipboard Converter",
        "back": "Back",
        "next": "Next",
        "install": "Install",
        "installing": "Installing...",
        "finish": "Finish",
        "rescan": "Rescan",
        "installed_tag": "Installed",
        "not_installed_tag": "Not installed",
        "active_tag": "Active",
        "vn_status_on": "Vietnamese: ON",
        "vn_status_off": "English: OFF",

        # Compact / Advanced Mode Toggle
        "btn_expand_adv": "▼ Show Advanced Options (Typing Rules, Macros, Per-App, System)",
        "btn_collapse_adv": "▲ Hide Advanced Options",

        # Tabs (Advanced Mode)
        "tab_general": "1. Typing Rules",
        "tab_typing": "1. Typing Rules",
        "tab_macro": "2. Macros",
        "tab_apps": "3. Applications",
        "tab_system": "4. System & Theme",

        # Setup Panel - Basic Card
        "frame_main": " Core Settings ",
        "lbl_framework": "Backend:",
        "fw_auto": "Auto",
        "fw_ibus": "IBus",
        "fw_fcitx5": "Fcitx5",
        "fw_fcitx": "Fcitx4",
        "fw_uinput": "UInput (Kernel)",
        "lbl_charset": "Charset:",
        "cs_unicode": "Unicode (Precomposed NFC)",
        "cs_combining": "Unicode (Combining NFD)",
        "cs_tcvn3": "TCVN3 (ABC)",
        "cs_vni_win": "VNI Windows",
        "cs_ascii": "Strip Diacritics (ASCII)",
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
        "lbl_icon_style": "Tray icon style:",
        "ic_flag_us": "Flat Flag VN / US (Default)",
        "ic_flag_uk": "Flat Flag VN / UK",
        "ic_badge": "Flat V / E Badge (UniKey)",
        "ic_lotus": "LotusKey Flower",
        "ic_symbolic": "Monochrome (Symbolic)",

        # Setup Panel - Tab 1: Output Mode & Typing Options
        "frame_output": " Output Mode ",
        "lbl_output_mode": "Output mode:",
        "out_preedit": "Pre-edit (Default, most reliable)",
        "out_surrounding": "Surrounding Text (Direct replacement)",
        "out_forward": "Forward Backspace (Legacy X11 / Terminals)",
        "lbl_restore_key": "Word restore key:",
        "rk_esc": "Esc key (Restore active word to raw English)",
        "rk_shift_bs": "Shift + Backspace",
        "rk_none": "Disabled",
        "frame_options": " Orthography & Typing Rules ",
        "opt_bilingual": "Auto-restore English words",
        "opt_modern": "Modern tone placement (oà, uý)",
        "opt_free_tone": "Free tone marking (SEN Flex)",
        "opt_quick_telex": "Consonant shorthand (cc=ch, gg=gi, nn=ng)",
        "opt_w2u": "Convert initial W to Ư",
        "opt_bracket": "Map [ to ơ and ] to ư",
        "opt_underline": "Underline pre-edit text",
        "opt_grave_menu": "Press ` for Quick Menu (double-tap `` for literal `)",
        "opt_autostart": "Start automatically on login",

        # Setup Panel - Tab 2: Macro Tab
        "opt_macro_enable": "Enable macro expansion",
        "opt_macro_cap": "Automatically match uppercase / lowercase expansion",
        "opt_macro_off": "Allow macro expansion even when Vietnamese mode is OFF",
        "btn_macro_rules": "⚙ Macro Rules ▾",
        "btn_macro_io": "📁 Import / Export ▾",
        "ph_macro_search": "🔍 Filter shortcuts or expansions...",
        "ph_macro_key": "Shortcut (e.g. vn)",
        "ph_macro_val": "Expansion (e.g. Việt Nam)",
        "btn_macro_add": "Add / Update",
        "btn_macro_del": "Delete",
        "btn_macro_import": "📥 Import...",
        "btn_macro_export": "📤 Export...",
        "col_macro_key": "Shortcut",
        "col_macro_val": "Expansion",

        # Setup Panel - Tab 3: Per-App & Exclusion Rules
        "frame_app_smart": " Smart Per-App State ",
        "opt_per_app": "Remember Vietnamese / English state per application window",
        "opt_disable_url": "Automatically bypass Vietnamese in URL bars and password fields",
        "frame_app_exclude": " Excluded Applications (Auto-switch to English) ",
        "ph_app_exclude": "Process name or WM_CLASS (e.g. kitty, code, steam)",
        "btn_app_add": "Add",
        "btn_app_del": "Remove",
        "btn_app_presets": "➕ Add Preset Group ▾",
        "btn_app_preset_term": "+ Terminals (kitty, Alacritty, wezterm, foot, konsole)",
        "btn_app_preset_ide": "+ VS Code / IDEs (code, codium, cursor, jetbrains, nvim)",
        "btn_app_preset_games": "+ Games / Steam (steam, lutris, heroic, prismlauncher)",
        "btn_app_preset_pass": "+ Password Managers (keepassxc, bitwarden, 1password)",

        # Setup Panel - Tab 4: System & Appearance
        "frame_system": " System & Startup ",
        "frame_appearance": " Appearance & Theme ",
        "lbl_theme": "Dialog theme:",
        "theme_auto": "Follow System (Auto)",
        "theme_dark": "Lotus Dark",
        "theme_light": "Lotus Light",
        "btn_sync_now": "⚡ Check & Re-sync Input Framework Now",
        "sync_ok_msg": "Successfully synchronized with backend: {fw}",

        # Clipboard Charset Converter Dialog
        "conv_title": "Clipboard & Text Charset Converter",
        "conv_src_label": "Source charset:",
        "conv_dst_label": "Target charset:",
        "conv_swap_btn": "⇄ Swap",
        "conv_case_label": "Case transform:",
        "case_none": "Keep original case",
        "case_upper": "UPPERCASE",
        "case_lower": "lowercase",
        "case_title": "Title Case",
        "conv_placeholder": "Type or paste text to transcode here...",
        "conv_btn_clipboard": "📋 Convert Clipboard Now",
        "conv_btn_text": "⚡ Convert Text Box",
        "conv_btn_copy": "📑 Copy Result",
        "conv_status_ready": "Ready for bidirectional conversion (Unicode ↔ TCVN3 ↔ VNI ↔ Combining ↔ ASCII).",
        "conv_status_done": "✔ Converted ({n} chars) from {src} → {dst} and updated Clipboard!",
        "conv_status_empty": "⚠ Clipboard is currently empty.",

        # Notifications
        "notify_saved_body": "Settings saved ({fw})\nMethod: {im} • Shortcut: {tg}",

        # Quick Menu
        "qm_enable_vn": "Vietnamese input",
        "qm_input_method": "Input method",
        "qm_charset": "Charset",
        "qm_framework": "Backend",
        "qm_output_mode": "Output mode",
        "qm_icon_style": "Tray icon",
        "qm_options": "Quick options",
        "qm_cs_unicode": "Unicode (NFC)",
        "qm_cs_combining": "Combining (NFD)",
        "qm_ic_flag_us": "Flag VN / US",
        "qm_ic_flag_uk": "Flag VN / UK",
        "qm_ic_badge": "V / E Badge",
        "qm_ic_lotus": "Lotus Flower",
        "qm_ic_symbolic": "Symbolic",
        "qm_open_setup": "⚙ Full Settings",
        "qm_open_conv": "🔄 Converter",
        "qm_hint": "` Quick Menu • `` literal ` • Ctrl+Shift toggle • Esc close",

        # Setup Wizard
        "scan_distro": "Linux Distribution",
        "scan_session": "Display Session",
        "scan_im": "Input Method Frameworks",
        "scan_gcc": "C Compiler (GCC/Clang)",
        "scan_installed": "Installed",
        "scan_missing": "Not installed (Using prebuilt binaries)",
        "scan_core": "LotusKey C-ABI Core",
        "scan_abi_ok": "Compatible (OK)",
        "scan_gtk": "GTK3 UI Runtime",
        "scan_ready": "Ready",
        "wiz_step_1": "1. Overview",
        "wiz_step_2": "2. System Check",
        "wiz_step_3": "3. Install",
        "wiz_step_4": "4. Finish",
        "wiz_welcome_head": "LotusKey Installer",
        "wiz_welcome_desc": "Configure Vietnamese input method for Linux (Wayland and X11).",
        "wiz_welcome_body": (
            "<b>LotusKey</b> supports Vietnamese input across IBus, Fcitx5, and UInput:\n\n"
            "• Input methods: Telex, VNI, Telex + VNI.\n"
            "• Flat Flag Icons (VN / US / UK), V/E Badge, Lotus Flower, Symbolic.\n"
            "• Charsets: Unicode NFC, Unicode NFD, TCVN3, VNI Windows.\n"
            "• English word auto-restore (or press Esc) and macro expansion.\n"
            "• Works on GNOME, KDE Plasma, Hyprland, Sway, XFCE, and Cinnamon."
        ),
        "wiz_chk_autostart": "Start automatically on login",
        "wiz_chk_open_cfg": "Open settings after installation",
        "wiz_chk_open_now": "Open LotusKey Settings now",
        "wiz_scan_head": "System Environment Check",
        "wiz_scan_desc": "Status of required components:",
        "wiz_inst_head": "Installing LotusKey",
        "wiz_inst_prep": "Preparing...",
        "wiz_inst_running": "Running ({i}/{total}): {name}...",
        "wiz_inst_fail": "Installation failed. See detailed log below.",
        "wiz_inst_done": "Installation completed.",
        "wiz_log_label": "Build & install log",
        "wiz_inst_log": "Build & install log",
        "wiz_s1": "Initialize configuration and flat flag SVG icons",
        "wiz_s2": "Compile C engines (IBus and UInput)",
        "wiz_s3": "Register input method component",
        "wiz_s4": "Create CLI links and desktop entry",
        "wiz_s5": "Configure login autostart (lotuskey-autostart)",
        "wiz_s6": "Activate and synchronize input method",
        "wiz_fin_head": "Installation Complete",
        "wiz_finish_head": "Installation Complete",
        "wiz_fin_desc": "LotusKey is ready to use.",
        "wiz_finish_desc": "LotusKey is ready to use.",
        "wiz_fin_summary": (
            "<b>Default configuration:</b>\n"
            "• Input method: <b>Telex</b>  •  Icon style: <b>Flat Flag VN / US</b>\n"
            "• Toggle shortcut: <b>Ctrl + Shift</b> or <b>Alt + Z</b>\n"
            "• Word restore key: <b>Esc</b>\n"
            "• Quick Menu key: <b>`</b> (grave)  •  Settings: <tt>lotuskey-setup</tt>"
        ),
        "wiz_finish_body": (
            "<b>Default configuration:</b>\n"
            "• Input method: <b>Telex</b>  •  Icon style: <b>Flat Flag VN / US</b>\n"
            "• Toggle shortcut: <b>Ctrl + Shift</b> or <b>Alt + Z</b>\n"
            "• Word restore key: <b>Esc</b>\n"
            "• Quick Menu key: <b>`</b> (grave)  •  Settings: <tt>lotuskey-setup</tt>"
        ),
        "wiz_btn_cancel": "Cancel",
        "wiz_btn_back": "Back",
        "wiz_btn_next": "Next",
        "wiz_btn_install": "Install",
        "wiz_btn_installing": "Installing...",
        "wiz_btn_finish": "Finish",
        "wiz_btn_rescan": "Rescan",
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
