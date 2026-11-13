#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Configuration Manager
Manages config.json, config.env, macros.conf, and autostart entries.
"""
import json
import os

from config.im_framework import resolve_effective_framework, get_uinput_binary

CONFIG_DIR = os.path.expanduser("~/.config/LotusKey")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CONFIG_ENV_FILE = os.path.join(CONFIG_DIR, "config.env")
MACROS_JSON_FILE = os.path.join(CONFIG_DIR, "macros.json")
MACROS_CONF_FILE = os.path.join(CONFIG_DIR, "macros.conf")

AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "lotuskey.desktop")

DEFAULT_CONFIG = {
    "enabled": True,
    "ui_lang": "vi",             # "vi" or "en"
    "input_method": 0,           # 0: Telex, 1: VNI, 2: Telex+VNI
    "output_mode": "preedit",    # "preedit", "surrounding", "forward"
    "im_framework": "auto",      # "auto", "ibus", "fcitx5", "fcitx", "uinput"
    "charset": 0,                # 0: Unicode NFC, 31: Unicode NFD, 27: TCVN3, 34: VNI Windows
    "free_tone_marking": True,
    "modern_tone_style": True,
    "auto_correct": True,
    "w2u": True,
    "bracket_transform": True,
    "macro_enabled": True,
    "toggle_key": "Both",        # "Both", "Control+Shift", "Alt+Z", "Shift+Space", "None"
    "mode_menu_key": "grave",    # "grave", "None"
    "quick_telex": False,
    "preedit_underline": False,
    "autostart": True,
}

DEFAULT_MACROS = [
    {"key": "vn", "value": "Việt Nam"},
    {"key": "hcm", "value": "TP. Hồ Chí Minh"},
    {"key": "hn", "value": "Hà Nội"},
    {"key": "ko", "value": "không"},
    {"key": "dc", "value": "được"},
    {"key": "ng", "value": "người"},
]


def _secure_dir(path: str) -> None:
    os.makedirs(path, mode=0o700, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _secure_file(path: str) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def is_autostart_enabled() -> bool:
    if not os.path.exists(AUTOSTART_FILE):
        return False
    try:
        with open(AUTOSTART_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            return "X-GNOME-Autostart-enabled=false" not in content and "Hidden=true" not in content
    except OSError:
        return False


def set_autostart(enabled: bool, preferred_framework: str = "auto") -> None:
    try:
        os.makedirs(AUTOSTART_DIR, exist_ok=True)
        if enabled:
            effective = resolve_effective_framework(preferred_framework)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if effective == "fcitx5":
                engine_exec = "fcitx5 -d"
                comment = "LotusKey Vietnamese Input (Fcitx5)"
            elif effective == "fcitx":
                engine_exec = "fcitx -d"
                comment = "LotusKey Vietnamese Input (Fcitx4)"
            elif effective == "uinput":
                engine_exec = f"{get_uinput_binary()} --daemon"
                comment = "LotusKey Vietnamese Input (UInput)"
            else:
                local_engine = os.path.join(base_dir, "bin", "ibus-engine-lotuskey")
                sys_engine = "/usr/lib/lotuskey/ibus-engine-lotuskey"
                bin_path = local_engine if os.path.exists(local_engine) else sys_engine
                engine_exec = f"{bin_path} --ibus"
                comment = "LotusKey Vietnamese Input (IBus)"

            from config.distro_adapter import DistroAdapter
            icon_path = DistroAdapter.get_icon_path(active=True)

            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=LotusKey\n"
                f"Comment={comment}\n"
                f"Exec={engine_exec}\n"
                f"Icon={icon_path}\n"
                "Terminal=false\n"
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            if os.path.exists(AUTOSTART_FILE):
                os.remove(AUTOSTART_FILE)
    except OSError:
        pass


def load_macros():
    _secure_dir(CONFIG_DIR)
    if os.path.exists(MACROS_JSON_FILE):
        try:
            with open(MACROS_JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    if os.path.exists(MACROS_CONF_FILE):
        macros = []
        try:
            with open(MACROS_CONF_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    macros.append({"key": k.strip(), "value": v.strip()})
            return macros
        except Exception:
            pass
    save_macros(DEFAULT_MACROS)
    return [m.copy() for m in DEFAULT_MACROS]


def save_macros(macros) -> bool:
    try:
        _secure_dir(CONFIG_DIR)
        with open(MACROS_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(macros, f, indent=4, ensure_ascii=False)
        _secure_file(MACROS_JSON_FILE)
        with open(MACROS_CONF_FILE, "w", encoding="utf-8") as f:
            f.write("# LotusKey Macros (key=value)\n")
            for item in macros:
                k = str(item.get("key", "")).strip()
                v = str(item.get("value", "")).strip()
                if k and v and "=" not in k:
                    f.write(f"{k}={v}\n")
        _secure_file(MACROS_CONF_FILE)
        return True
    except OSError:
        return False


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
                elif k == "UI_LANG":
                    cfg_updates["ui_lang"] = "en" if v.lower().startswith("en") else "vi"
                elif k == "INPUT_METHOD":
                    if "telex_vni" in v.lower():
                        cfg_updates["input_method"] = 2
                    elif "vni" in v.lower():
                        cfg_updates["input_method"] = 1
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
                elif k == "MACRO_ENABLED":
                    cfg_updates["macro_enabled"] = (v.lower() not in ("false", "0"))
                elif k == "OUTPUT_MODE":
                    cfg_updates["output_mode"] = v
                elif k == "IM_FRAMEWORK":
                    cfg_updates["im_framework"] = v
                elif k == "CHARSET":
                    try:
                        cfg_updates["charset"] = int(v)
                    except ValueError:
                        pass
                elif k == "AUTOSTART":
                    cfg_updates["autostart"] = (v.lower() not in ("false", "0"))
    except OSError:
        pass
    return cfg_updates


def load_config():
    _secure_dir(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE) and not os.path.exists(CONFIG_ENV_FILE):
        save_config(DEFAULT_CONFIG)
        load_macros()
        return DEFAULT_CONFIG.copy()

    cfg = DEFAULT_CONFIG.copy()

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved_json = json.load(f)
                if isinstance(saved_json, dict):
                    cfg.update(saved_json)
        except Exception:
            pass

    if os.path.exists(CONFIG_ENV_FILE):
        try:
            env_mtime = os.path.getmtime(CONFIG_ENV_FILE)
            json_mtime = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0
            if env_mtime > json_mtime:
                env_updates = _parse_env_file()
                cfg.update(env_updates)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4, ensure_ascii=False)
                _secure_file(CONFIG_FILE)
        except OSError:
            pass

    if not os.path.exists(CONFIG_ENV_FILE):
        _write_env_file(cfg)
    if not os.path.exists(MACROS_CONF_FILE):
        load_macros()

    if "autostart" not in cfg:
        cfg["autostart"] = is_autostart_enabled()
    if cfg.get("ui_lang") not in ("vi", "en"):
        cfg["ui_lang"] = "vi"

    return cfg


def _write_env_file(cfg) -> None:
    try:
        _secure_dir(CONFIG_DIR)
        im_val = cfg.get("input_method", 0)
        im_name = "vni" if im_val == 1 else ("telex_vni" if im_val == 2 else "telex")
        ui_lang = "en" if str(cfg.get("ui_lang", "vi")).startswith("en") else "vi"
        with open(CONFIG_ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f'ENABLED="{"true" if cfg.get("enabled", True) else "false"}"\n')
            f.write(f'UI_LANG="{ui_lang}"\n')
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
            f.write(f'MACRO_ENABLED="{"true" if cfg.get("macro_enabled", True) else "false"}"\n')
            f.write(f'OUTPUT_MODE="{cfg.get("output_mode", "preedit")}"\n')
            f.write(f'IM_FRAMEWORK="{cfg.get("im_framework", "auto")}"\n')
            f.write(f'CHARSET="{cfg.get("charset", 0)}"\n')
            f.write(f'AUTOSTART="{"true" if cfg.get("autostart", True) else "false"}"\n')
        _secure_file(CONFIG_ENV_FILE)
    except OSError:
        pass


def save_config(cfg) -> bool:
    try:
        _secure_dir(CONFIG_DIR)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        _secure_file(CONFIG_FILE)
        _write_env_file(cfg)
        if "autostart" in cfg:
            set_autostart(cfg["autostart"], cfg.get("im_framework", "auto"))
        return True
    except OSError:
        return False
