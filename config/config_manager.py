#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Configuration Manager
Handles persistence and bidirectional synchronization between config.json and config.env.
"""
import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/LotusKey")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CONFIG_ENV_FILE = os.path.join(CONFIG_DIR, "config.env")

AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "lotuskey.desktop")

DEFAULT_CONFIG = {
    "enabled": True,             # Trạng thái gõ tiếng Việt (True = VN, False = EN)
    "input_method": 0,           # Kiểu gõ: 0: Telex, 1: VNI, 2: Telex+VNI
    "output_mode": "preedit",    # Chế độ gửi phím: "preedit", "surrounding", "forward"
    "charset": 0,                # Bảng mã: 0: Unicode UTF-8, 31: Unicode Tổ hợp, 27: TCVN3, 34: VNI Windows
    "free_tone_marking": True,   # Bỏ dấu tự do (Free-tone marking)
    "modern_tone_style": True,   # Bỏ dấu kiểu mới (Modern orthography: oà, uý)
    "auto_correct": True,        # Song ngữ thông minh (Smart Bilingual)
    "w2u": True,                 # Gõ nhanh W thành Ư (W to Ư)
    "bracket_transform": True,   # Gõ nhanh [ thành ơ và ] thành ư (Bracket transform)
    "toggle_key": "Both",        # Hotkey chuyển Anh/Việt: "Both", "Control+Shift", "Alt+Z", "Shift+Space", "None"
    "mode_menu_key": "grave",    # Phím tắt Quick Menu: "grave" (phím `), "None"
    "quick_telex": False,        # Gõ tắt phụ âm nhanh (Quick Telex: cc=ch, gg=gi...)
    "preedit_underline": False,  # Gạch chân chữ đang đệm (Pre-edit underline)
    "autostart": True,           # Khởi động cùng hệ thống (Autostart with OS)
}

def is_autostart_enabled():
    if not os.path.exists(AUTOSTART_FILE):
        return False
    try:
        with open(AUTOSTART_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            return "X-GNOME-Autostart-enabled=false" not in content and "Hidden=true" not in content
    except Exception:
        return False

def set_autostart(enabled: bool):
    try:
        os.makedirs(AUTOSTART_DIR, exist_ok=True)
        if enabled:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            local_engine = os.path.join(base_dir, "bin", "ibus-engine-lotuskey")
            sys_engine = "/usr/lib/lotuskey/ibus-engine-lotuskey"
            engine_exec = local_engine if os.path.exists(local_engine) else sys_engine
            content = f"""[Desktop Entry]
Type=Application
Name=LotusKey
Comment=Bộ gõ tiếng Việt LotusKey (IBus Wayland)
Exec={engine_exec} --ibus
Icon=/usr/share/icons/hicolor/scalable/apps/fcitx-lotus.svg
Terminal=false
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
            with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            if os.path.exists(AUTOSTART_FILE):
                os.remove(AUTOSTART_FILE)
    except Exception as e:
        print(f"Error setting autostart: {e}")

def _parse_env_file():
    cfg_updates = {}
    if not os.path.exists(CONFIG_ENV_FILE):
        return cfg_updates
    try:
        with open(CONFIG_ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "ENABLED":
                    cfg_updates["enabled"] = (v.lower() not in ("false", "0"))
                elif k == "INPUT_METHOD":
                    if "vni" in v.lower():
                        cfg_updates["input_method"] = 1
                    elif "telex_vni" in v.lower():
                        cfg_updates["input_method"] = 2
                    else:
                        cfg_updates["input_method"] = 0
                elif k == "GRAMMAR_PROFILE":
                    cfg_updates["free_tone_marking"] = ("classic" not in v.lower())
                elif k == "SMART_BILINGUAL":
                    cfg_updates["auto_correct"] = (v.lower() not in ("false", "0"))
                elif k == "MODERN_ORTHOGRAPHY":
                    cfg_updates["modern_tone_style"] = (v.lower() not in ("false", "0"))
                elif k == "QUICK_TELEX":
                    cfg_updates["quick_telex"] = (v.lower() in ("true", "1"))
                elif k == "PREEDIT_UNDERLINE":
                    cfg_updates["preedit_underline"] = (v.lower() in ("true", "1"))
                elif k == "MODE_MENU_KEY":
                    cfg_updates["mode_menu_key"] = v
                elif k == "TOGGLE_KEY":
                    cfg_updates["toggle_key"] = v
                elif k == "W2U":
                    cfg_updates["w2u"] = (v.lower() not in ("false", "0"))
                elif k == "BRACKET_TRANSFORM":
                    cfg_updates["bracket_transform"] = (v.lower() not in ("false", "0"))
                elif k == "OUTPUT_MODE":
                    cfg_updates["output_mode"] = v
                elif k == "CHARSET":
                    try:
                        cfg_updates["charset"] = int(v)
                    except ValueError:
                        pass
                elif k == "AUTOSTART":
                    cfg_updates["autostart"] = (v.lower() not in ("false", "0"))
    except Exception as e:
        print(f"Error parsing config.env: {e}")
    return cfg_updates

def load_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE) and not os.path.exists(CONFIG_ENV_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    cfg = DEFAULT_CONFIG.copy()

    # Load from config.json if exists
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved_json = json.load(f)
                cfg.update(saved_json)
        except Exception as e:
            print(f"Error loading config.json: {e}")

    # If config.env exists and is newer than config.json, sync from config.env
    if os.path.exists(CONFIG_ENV_FILE):
        try:
            env_mtime = os.path.getmtime(CONFIG_ENV_FILE)
            json_mtime = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0
            if env_mtime > json_mtime:
                env_updates = _parse_env_file()
                cfg.update(env_updates)
                # Persist merged state to config.json
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error syncing config.env to json: {e}")

    # Ensure config.env exists and is synced
    if not os.path.exists(CONFIG_ENV_FILE):
        _write_env_file(cfg)

    # Sync autostart status with filesystem if not explicitly configured
    if "autostart" not in cfg:
        cfg["autostart"] = is_autostart_enabled()

    return cfg

def _write_env_file(cfg):
    try:
        im_val = cfg.get("input_method", 0)
        im_name = "vni" if im_val == 1 else ("telex_vni" if im_val == 2 else "telex")
        with open(CONFIG_ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f'ENABLED="{"true" if cfg.get("enabled", True) else "false"}"\n')
            f.write(f'INPUT_METHOD="{im_name}"\n')
            f.write(f'GRAMMAR_PROFILE="{"sen_flex" if cfg.get("free_tone_marking", True) else "classic"}"\n')
            f.write(f'SMART_BILINGUAL="{"true" if cfg.get("auto_correct", True) else "false"}"\n')
            f.write(f'MODERN_ORTHOGRAPHY="{"true" if cfg.get("modern_tone_style", True) else "false"}"\n')
            f.write(f'QUICK_TELEX="{"true" if cfg.get("quick_telex", False) else "false"}"\n')
            f.write(f'PREEDIT_UNDERLINE="{"true" if cfg.get("preedit_underline", False) else "false"}"\n')
            f.write(f'MODE_MENU_KEY="{cfg.get("mode_menu_key", "grave")}"\n')
            f.write(f'TOGGLE_KEY="{cfg.get("toggle_key", "Both")}"\n')
            f.write(f'W2U="{"true" if cfg.get("w2u", True) else "false"}"\n')
            f.write(f'BRACKET_TRANSFORM="{"true" if cfg.get("bracket_transform", True) else "false"}"\n')
            f.write(f'OUTPUT_MODE="{cfg.get("output_mode", "preedit")}"\n')
            f.write(f'CHARSET="{cfg.get("charset", 0)}"\n')
            f.write(f'AUTOSTART="{"true" if cfg.get("autostart", True) else "false"}"\n')
    except Exception as e:
        print(f"Error writing config.env: {e}")

def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        # 1. Write config.json
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        # 2. Write config.env
        _write_env_file(cfg)
        # 3. Apply autostart desktop entry
        if "autostart" in cfg:
            set_autostart(cfg["autostart"])
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
