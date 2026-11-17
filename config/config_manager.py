#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LotusKey - Configuration Manager
Manages config.json, config.env, macros.conf, autostart entries,
macro import/export (UniKey/EVKey .txt & .json), and bidirectional charset conversion.
"""
import json
import os
import unicodedata
from typing import Any, Dict, List, Tuple

from config.im_framework import resolve_effective_framework, get_uinput_binary

CONFIG_DIR = os.path.expanduser("~/.config/LotusKey")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CONFIG_ENV_FILE = os.path.join(CONFIG_DIR, "config.env")
MACROS_JSON_FILE = os.path.join(CONFIG_DIR, "macros.json")
MACROS_CONF_FILE = os.path.join(CONFIG_DIR, "macros.conf")

AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "lotuskey.desktop")

DEFAULT_EXCLUDED_APPS = [
    "kitty",
    "Alacritty",
    "wezterm",
    "foot",
    "gnome-terminal-server",
    "konsole",
]

DEFAULT_CONFIG: Dict[str, Any] = {
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
    "macro_in_off_mode": False,
    "auto_capitalize_macro": True,
    "per_app_remember": True,
    "auto_disable_url_bar": True,
    "compact_mode": True,
    "toggle_key": "Both",        # "Both", "Control+Shift", "Alt+Z", "Shift+Space", "None"
    "mode_menu_key": "grave",    # "grave", "None"
    "quick_telex": False,
    "preedit_underline": False,
    "autostart": True,
    "icon_style": "flag",        # "flag", "badge", "lotus", "symbolic"
    "flag_variant": "us",        # "us", "uk"
    "restore_key": "esc",        # "esc", "shift_backspace", "none"
    "theme": "auto",             # "auto", "dark", "light"
    "excluded_apps": list(DEFAULT_EXCLUDED_APPS),
}

DEFAULT_MACROS: List[Dict[str, str]] = [
    {"key": "vn", "value": "Việt Nam"},
    {"key": "hcm", "value": "TP. Hồ Chí Minh"},
    {"key": "hn", "value": "Hà Nội"},
    {"key": "ko", "value": "không"},
    {"key": "dc", "value": "được"},
    {"key": "ng", "value": "người"},
]

# 134 Vietnamese character mappings: (Unicode NFC, Unicode Combining, TCVN3, VNI Windows, ASCII base)
CHARSET_TABLE: List[Tuple[str, str, str, str, str]] = [
    ("À", "A\u0300", "µ", "AØ", "A"), ("Á", "A\u0301", "¸", "AÙ", "A"), ("Â", "Â", "¢", "AÂ", "A"), ("Ã", "A\u0303", "·", "AÕ", "A"),
    ("È", "E\u0300", "Ì", "EØ", "E"), ("É", "E\u0301", "Ð", "EÙ", "E"), ("Ê", "Ê", "£", "EÂ", "E"), ("Ì", "I\u0300", "×", "Ì", "I"),
    ("Í", "I\u0301", "Ý", "Í", "I"),  ("Ò", "O\u0300", "ß", "OØ", "O"), ("Ó", "O\u0301", "ã", "OÙ", "O"), ("Ô", "Ô", "¤", "OÂ", "O"),
    ("Õ", "O\u0303", "â", "OÕ", "O"), ("Ù", "U\u0300", "ï", "UØ", "U"), ("Ú", "U\u0301", "ó", "UÙ", "U"), ("Ý", "Y\u0301", "ý", "YÙ", "Y"),
    ("à", "a\u0300", "µ", "aø", "a"), ("á", "a\u0301", "¸", "aù", "a"), ("â", "â", "©", "aâ", "a"), ("ã", "a\u0303", "·", "aõ", "a"),
    ("è", "e\u0300", "Ì", "eø", "e"), ("é", "e\u0301", "Ð", "eù", "e"), ("ê", "ê", "ª", "eâ", "e"), ("ì", "i\u0300", "×", "ì", "i"),
    ("í", "i\u0301", "Ý", "í", "i"),  ("ò", "o\u0300", "ß", "oø", "o"), ("ó", "o\u0301", "ã", "où", "o"), ("ô", "ô", "«", "oâ", "o"),
    ("õ", "o\u0303", "â", "oõ", "o"), ("ù", "u\u0300", "ï", "uø", "u"), ("ú", "u\u0301", "ó", "uù", "u"), ("ý", "y\u0301", "ý", "yù", "y"),
    ("Ă", "Ă", "¡", "AÊ", "A"), ("ă", "ă", "¨", "aê", "a"), ("Đ", "Đ", "§", "Ñ", "D"),  ("đ", "đ", "®", "ñ", "d"),
    ("Ĩ", "I\u0303", "Ü", "Ó", "I"),  ("ĩ", "i\u0303", "Ü", "ó", "i"),  ("Ũ", "U\u0303", "ò", "UÕ", "U"), ("ũ", "u\u0303", "ò", "uõ", "u"),
    ("Ơ", "Ơ", "¥", "Ô", "O"),  ("ơ", "ơ", "¬", "ô", "o"),  ("Ư", "Ư", "¦", "Ö", "U"),  ("ư", "ư", "\u00ad", "ö", "u"),
    ("Ạ", "A\u0323", "¹", "AÏ", "A"), ("ạ", "a\u0323", "¹", "aï", "a"), ("Ả", "A\u0309", "¶", "AÛ", "A"), ("ả", "a\u0309", "¶", "aû", "a"),
    ("Ấ", "Â\u0301", "Ê", "AÁ", "A"), ("ấ", "â\u0301", "Ê", "aá", "a"), ("Ầ", "Â\u0300", "Ç", "AÀ", "A"), ("ầ", "â\u0300", "Ç", "aà", "a"),
    ("Ẩ", "Â\u0309", "È", "AÅ", "A"), ("ẩ", "â\u0309", "È", "aå", "a"), ("Ẫ", "Â\u0303", "É", "AÃ", "A"), ("ẫ", "â\u0303", "É", "aã", "a"),
    ("Ậ", "Â\u0323", "Ë", "AÄ", "A"), ("ậ", "â\u0323", "Ë", "aä", "a"), ("Ắ", "Ă\u0301", "¾", "AÉ", "A"), ("ắ", "ă\u0301", "¾", "aé", "a"),
    ("Ằ", "Ă\u0300", "»", "AÈ", "A"), ("ằ", "ă\u0300", "»", "aè", "a"), ("Ẳ", "Ă\u0309", "¼", "AÚ", "A"), ("ẳ", "ă\u0309", "¼", "aú", "a"),
    ("Ẵ", "Ă\u0303", "½", "AÜ", "A"), ("ẵ", "ă\u0303", "½", "aü", "a"), ("Ặ", "Ă\u0323", "Æ", "AË", "A"), ("ặ", "ă\u0323", "Æ", "aë", "a"),
    ("Ẹ", "E\u0323", "Ñ", "EÏ", "E"), ("ẹ", "e\u0323", "Ñ", "eï", "e"), ("Ẻ", "E\u0309", "Î", "EÛ", "E"), ("ẻ", "e\u0309", "Î", "eû", "e"),
    ("Ẽ", "E\u0303", "Ï", "EÕ", "E"), ("ẽ", "e\u0303", "Ï", "eõ", "e"), ("Ế", "Ê\u0301", "Õ", "EÁ", "E"), ("ế", "ê\u0301", "Õ", "eá", "e"),
    ("Ề", "Ê\u0300", "Ò", "EÀ", "E"), ("ề", "ê\u0300", "Ò", "eà", "e"), ("Ể", "Ê\u0309", "Ó", "EÅ", "E"), ("ể", "ê\u0309", "Ó", "eå", "e"),
    ("Ễ", "Ê\u0303", "Ô", "EÃ", "E"), ("ễ", "ê\u0303", "Ô", "eã", "e"), ("Ệ", "Ê\u0323", "Ö", "EÄ", "E"), ("ệ", "ê\u0323", "Ö", "eä", "e"),
    ("Ỉ", "I\u0309", "Ø", "Æ", "I"),  ("ỉ", "i\u0309", "Ø", "æ", "i"),  ("Ị", "I\u0323", "Þ", "Ò", "I"),  ("ị", "i\u0323", "Þ", "ò", "i"),
    ("Ọ", "O\u0323", "ä", "OÏ", "O"), ("ọ", "o\u0323", "ä", "oï", "o"), ("Ỏ", "O\u0309", "á", "OÛ", "O"), ("ỏ", "o\u0309", "á", "oû", "o"),
    ("Ố", "Ô\u0301", "è", "OÁ", "O"), ("ố", "ô\u0301", "è", "oá", "o"), ("Ồ", "Ô\u0300", "å", "OÀ", "O"), ("ồ", "ô\u0300", "å", "oà", "o"),
    ("Ổ", "Ô\u0309", "æ", "OÅ", "O"), ("ổ", "ô\u0309", "æ", "oå", "o"), ("Ỗ", "Ô\u0303", "ç", "OÃ", "O"), ("ỗ", "ô\u0303", "ç", "oã", "o"),
    ("Ộ", "Ô\u0323", "é", "OÄ", "O"), ("ộ", "ô\u0323", "é", "oä", "o"), ("Ớ", "Ơ\u0301", "í", "ÔÙ", "O"), ("ớ", "ơ\u0301", "í", "ôù", "o"),
    ("Ờ", "Ơ\u0300", "ê", "ÔØ", "O"), ("ờ", "ơ\u0300", "ê", "ôø", "o"), ("Ở", "Ơ\u0309", "ë", "ÔÛ", "O"), ("ở", "ơ\u0309", "ë", "ôû", "o"),
    ("Ỡ", "Ơ\u0303", "ì", "ÔÕ", "O"), ("ỡ", "ơ\u0303", "ì", "ôõ", "o"), ("Ợ", "Ơ\u0323", "î", "ÔÏ", "O"), ("ợ", "ơ\u0323", "î", "ôï", "o"),
    ("Ụ", "U\u0323", "ô", "UÏ", "U"), ("ụ", "u\u0323", "ô", "uï", "u"), ("Ủ", "U\u0309", "ñ", "UÛ", "U"), ("ủ", "u\u0309", "ñ", "uû", "u"),
    ("Ứ", "Ư\u0301", "ø", "ÖÙ", "U"), ("ứ", "ư\u0301", "ø", "öù", "u"), ("Ừ", "Ư\u0300", "õ", "ÖØ", "U"), ("ừ", "ư\u0300", "õ", "öø", "u"),
    ("Ử", "Ư\u0309", "ö", "ÖÛ", "U"), ("ử", "ư\u0309", "ö", "öû", "u"), ("Ữ", "Ư\u0303", "÷", "ÖÕ", "U"), ("ữ", "ư\u0303", "÷", "öõ", "u"),
    ("Ự", "Ư\u0323", "ù", "ÖÏ", "U"), ("ự", "ư\u0323", "ù", "öï", "u"), ("Ỳ", "Y\u0300", "ú", "YØ", "Y"), ("ỳ", "y\u0300", "ú", "yø", "y"),
    ("Ỵ", "Y\u0323", "þ", "Î", "Y"),  ("ỵ", "y\u0323", "þ", "î", "y"),  ("Ỷ", "Y\u0309", "û", "YÛ", "Y"), ("ỷ", "y\u0309", "û", "yû", "y"),
    ("Ỹ", "Y\u0303", "ü", "YÕ", "Y"), ("ỹ", "y\u0303", "ü", "yõ", "y"),
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
    if os.path.exists(AUTOSTART_FILE):
        try:
            with open(AUTOSTART_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                return "X-GNOME-Autostart-enabled=false" not in content and "Hidden=true" not in content
        except OSError:
            return False
    return os.path.exists("/etc/xdg/autostart/lotuskey.desktop")


def get_autostart_binary() -> str:
    import shutil
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(base_dir, "bin", "lotuskey-autostart"),
        os.path.abspath(os.path.join(base_dir, "..", "..", "bin", "lotuskey-autostart")),
        os.path.expanduser("~/.local/bin/lotuskey-autostart"),
        "/usr/local/bin/lotuskey-autostart",
        "/usr/bin/lotuskey-autostart",
    ]
    for cand in candidates:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return shutil.which("lotuskey-autostart") or ""


def set_autostart(enabled: bool, preferred_framework: str = "auto") -> None:
    try:
        os.makedirs(AUTOSTART_DIR, exist_ok=True)
        if enabled:
            effective = resolve_effective_framework(preferred_framework)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            autostart_bin = get_autostart_binary()

            if autostart_bin:
                engine_exec = autostart_bin
                comment = f"LotusKey Vietnamese Input ({effective.upper()})"
            elif effective == "fcitx5":
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
                prefix_engine = os.path.abspath(os.path.join(base_dir, "..", "..", "lib", "lotuskey", "ibus-engine-lotuskey"))
                sys_engine = "/usr/lib/lotuskey/ibus-engine-lotuskey"
                bin_path = (
                    local_engine if os.path.exists(local_engine)
                    else (prefix_engine if os.path.exists(prefix_engine) else sys_engine)
                )
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
            if os.path.exists("/etc/xdg/autostart/lotuskey.desktop"):
                content = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=LotusKey\n"
                    "Hidden=true\n"
                    "X-GNOME-Autostart-enabled=false\n"
                )
                with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
                    f.write(content)
            elif os.path.exists(AUTOSTART_FILE):
                os.remove(AUTOSTART_FILE)
    except OSError:
        pass


def load_macros() -> List[Dict[str, str]]:
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


def save_macros(macros: List[Dict[str, str]]) -> bool:
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


def import_macros_from_file(filepath: str, existing_macros: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """
    Imports macros from LotusKey .json or UniKey/EVKey .txt/.conf files.
    Merges into existing_macros (updating existing keys or appending new ones).
    """
    merged: List[Dict[str, str]] = [m.copy() for m in (existing_macros or [])]
    index_by_lower = {m["key"].lower(): idx for idx, m in enumerate(merged) if m.get("key")}

    if not filepath or not os.path.isfile(filepath):
        return merged

    new_items: List[Dict[str, str]] = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        stripped = raw.strip()
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        k = str(item.get("key", "")).strip()
                        v = str(item.get("value", "")).strip()
                        if k and v and " " not in k:
                            new_items.append({"key": k, "value": v})
        else:
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if "DO NOT DELETE THIS LINE" in line.upper():
                    continue
                sep = "=" if "=" in line else (":" if ":" in line else ("\t" if "\t" in line else None))
                if not sep:
                    continue
                k, v = line.split(sep, 1)
                k = k.strip()
                v = v.strip()
                if k and v and " " not in k and "=" not in k:
                    new_items.append({"key": k, "value": v})
    except Exception:
        return merged

    for item in new_items:
        kl = item["key"].lower()
        if kl in index_by_lower:
            merged[index_by_lower[kl]] = item
        else:
            index_by_lower[kl] = len(merged)
            merged.append(item)
    return merged


def export_macros_to_file(filepath: str, macros: List[Dict[str, str]]) -> bool:
    """Exports macros to .json or UniKey-compatible .txt format."""
    try:
        if filepath.lower().endswith(".json"):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(macros, f, indent=4, ensure_ascii=False)
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(";DO NOT DELETE THIS LINE*** version=1 ***\n")
                for item in macros:
                    k = str(item.get("key", "")).strip()
                    v = str(item.get("value", "")).strip()
                    if k and v:
                        f.write(f"{k}:{v}\n")
        return True
    except OSError:
        return False


def convert_vietnamese_text(
    text: str,
    src_charset: str = "unicode",
    dst_charset: str = "unicode",
    case_mode: str = "none",
) -> str:
    """
    Bidirectional Vietnamese charset converter.
    Supported charsets:
      - 'unicode'   : Unicode dựng sẵn (NFC)
      - 'combining' : Unicode tổ hợp (NFD / Combining)
      - 'tcvn3'     : TCVN3 (ABC)
      - 'vni'       : VNI Windows
      - 'ascii'     : Không dấu (ASCII stripped)
    Supported case_mode: 'none', 'upper', 'lower', 'title'
    """
    if not text:
        return ""

    src = src_charset.lower().strip()
    dst = dst_charset.lower().strip()

    # Step 1: Decode from source charset to Unicode NFC
    if src == "unicode":
        nfc_text = unicodedata.normalize("NFC", text)
    elif src == "combining":
        # Decode combining sequences to NFC
        nfc_text = unicodedata.normalize("NFC", text)
        for nfc_ch, comb_ch, _, _, _ in sorted(CHARSET_TABLE, key=lambda x: len(x[1]), reverse=True):
            if len(comb_ch) > 1 and comb_ch in nfc_text:
                nfc_text = nfc_text.replace(comb_ch, nfc_ch)
    elif src == "vni":
        # Include both standard VNI sequences and Title-Case VNI sequences (e.g. "Aù" -> "Á", "Oâ" -> "Ô")
        raw_vni_pairs: List[Tuple[str, str]] = [(entry[3], entry[0]) for entry in CHARSET_TABLE if entry[3]]
        for idx, entry in enumerate(CHARSET_TABLE):
            if entry[4].isupper() and len(entry[3]) > 1:
                low_idx = (idx + 16) if idx < 16 else (idx + 1 if (idx >= 32 and idx % 2 == 0) else -1)
                if 0 <= low_idx < len(CHARSET_TABLE):
                    low_vni = CHARSET_TABLE[low_idx][3]
                    if len(low_vni) > 1:
                        mixed_seq = entry[3][0] + low_vni[1:]
                        raw_vni_pairs.append((mixed_seq, entry[0]))
        vni_pairs = sorted(raw_vni_pairs, key=lambda p: len(p[0]), reverse=True)
        out_chars: List[str] = []
        i = 0
        n = len(text)
        while i < n:
            matched = False
            for vni_seq, nfc_ch in vni_pairs:
                vlen = len(vni_seq)
                if text.startswith(vni_seq, i):
                    out_chars.append(nfc_ch)
                    i += vlen
                    matched = True
                    break
            if not matched:
                out_chars.append(text[i])
                i += 1
        nfc_text = "".join(out_chars)
    elif src == "tcvn3":
        # In TCVN3, tone-marked vowels share byte codes between uppercase and lowercase.
        # Build both lowercase-preferred and uppercase-preferred maps for context-aware decoding.
        lower_map: Dict[str, str] = {}
        upper_map: Dict[str, str] = {}
        for nfc_ch, _, tcvn_ch, _, ascii_b in CHARSET_TABLE:
            if not tcvn_ch:
                continue
            if ascii_b.islower():
                lower_map.setdefault(tcvn_ch, nfc_ch)
            else:
                upper_map.setdefault(tcvn_ch, nfc_ch)
        for k, v in upper_map.items():
            lower_map.setdefault(k, v)
        for k, v in lower_map.items():
            upper_map.setdefault(k, v)
        tcvn_keys = sorted(lower_map.keys(), key=len, reverse=True)
        has_any_lower_ascii = any("a" <= c <= "z" for c in text)
        has_any_upper_ascii = any("A" <= c <= "Z" for c in text)
        out_chars = []
        i = 0
        n = len(text)
        while i < n:
            matched = False
            for tcvn_seq in tcvn_keys:
                tlen = len(tcvn_seq)
                if text.startswith(tcvn_seq, i):
                    prev_upper = i > 0 and ("A" <= text[i - 1] <= "Z")
                    prev2_upper = i > 1 and ("A" <= text[i - 2] <= "Z")
                    next_upper = (i + tlen < n) and ("A" <= text[i + tlen] <= "Z")
                    want_upper = next_upper or (
                        prev_upper and (prev2_upper or (not has_any_lower_ascii and has_any_upper_ascii))
                    )
                    out_chars.append(upper_map[tcvn_seq] if want_upper else lower_map[tcvn_seq])
                    i += tlen
                    matched = True
                    break
            if not matched:
                out_chars.append(text[i])
                i += 1
        nfc_text = "".join(out_chars)
    else:
        nfc_text = text

    # Step 2: Apply case transformation on Unicode NFC if requested
    c_mode = case_mode.lower().strip()
    if c_mode == "upper":
        nfc_text = nfc_text.upper()
    elif c_mode == "lower":
        nfc_text = nfc_text.lower()
    elif c_mode == "title":
        nfc_text = nfc_text.title()

    # Step 3: Encode from Unicode NFC to destination charset
    if dst == "unicode":
        return unicodedata.normalize("NFC", nfc_text)

    nfc_map: Dict[str, Tuple[str, str, str, str]] = {
        entry[0]: (entry[1], entry[2], entry[3], entry[4]) for entry in CHARSET_TABLE
    }
    result: List[str] = []
    for ch in nfc_text:
        if ch in nfc_map:
            comb_v, tcvn_v, vni_v, ascii_v = nfc_map[ch]
            if dst == "combining":
                result.append(comb_v)
            elif dst == "tcvn3":
                result.append(tcvn_v)
            elif dst == "vni":
                result.append(vni_v)
            elif dst == "ascii":
                result.append(ascii_v)
            else:
                result.append(ch)
        else:
            result.append(ch)
    return "".join(result)


def _parse_env_file() -> Dict[str, Any]:
    cfg_updates: Dict[str, Any] = {}
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
                elif k == "MACRO_IN_OFF_MODE":
                    cfg_updates["macro_in_off_mode"] = (v.lower() in ("true", "1"))
                elif k == "AUTO_CAPITALIZE_MACRO":
                    cfg_updates["auto_capitalize_macro"] = (v.lower() not in ("false", "0"))
                elif k == "PER_APP_REMEMBER":
                    cfg_updates["per_app_remember"] = (v.lower() not in ("false", "0"))
                elif k == "AUTO_DISABLE_URL_BAR":
                    cfg_updates["auto_disable_url_bar"] = (v.lower() not in ("false", "0"))
                elif k == "COMPACT_MODE":
                    cfg_updates["compact_mode"] = (v.lower() not in ("false", "0"))
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
                elif k == "ICON_STYLE":
                    if v.lower() in ("flag", "badge", "lotus", "symbolic"):
                        cfg_updates["icon_style"] = v.lower()
                elif k == "FLAG_VARIANT":
                    if v.lower() in ("us", "uk"):
                        cfg_updates["flag_variant"] = v.lower()
                elif k == "RESTORE_KEY":
                    if v.lower() in ("esc", "shift_backspace", "none"):
                        cfg_updates["restore_key"] = v.lower()
                elif k == "THEME":
                    if v.lower() in ("auto", "dark", "light"):
                        cfg_updates["theme"] = v.lower()
    except OSError:
        pass
    return cfg_updates


def load_config() -> Dict[str, Any]:
    _secure_dir(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE) and not os.path.exists(CONFIG_ENV_FILE):
        cfg_init = DEFAULT_CONFIG.copy()
        cfg_init["excluded_apps"] = list(DEFAULT_EXCLUDED_APPS)
        save_config(cfg_init)
        load_macros()
        return cfg_init

    cfg = DEFAULT_CONFIG.copy()
    cfg["excluded_apps"] = list(DEFAULT_EXCLUDED_APPS)

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
    if cfg.get("icon_style") not in ("flag", "badge", "lotus", "symbolic"):
        cfg["icon_style"] = "flag"
    if cfg.get("flag_variant") not in ("us", "uk"):
        cfg["flag_variant"] = "us"
    if cfg.get("restore_key") not in ("esc", "shift_backspace", "none"):
        cfg["restore_key"] = "esc"
    if cfg.get("theme") not in ("auto", "dark", "light"):
        cfg["theme"] = "auto"
    try:
        cs_val = int(cfg.get("charset", 0))
    except (ValueError, TypeError):
        cs_val = 0
    cfg["charset"] = {9: 31, 5: 27, 12: 34}.get(cs_val, cs_val if cs_val in (0, 31, 27, 34) else 0)
    if not isinstance(cfg.get("excluded_apps"), list):
        cfg["excluded_apps"] = list(DEFAULT_EXCLUDED_APPS)

    return cfg


def _write_env_file(cfg: Dict[str, Any]) -> None:
    try:
        _secure_dir(CONFIG_DIR)
        im_val = cfg.get("input_method", 0)
        im_name = "vni" if im_val == 1 else ("telex_vni" if im_val == 2 else "telex")
        ui_lang = "en" if str(cfg.get("ui_lang", "vi")).startswith("en") else "vi"
        icon_style = cfg.get("icon_style", "flag")
        flag_variant = cfg.get("flag_variant", "us")
        restore_key = cfg.get("restore_key", "esc")
        theme = cfg.get("theme", "auto")
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
            f.write(f'MACRO_IN_OFF_MODE="{"true" if cfg.get("macro_in_off_mode", False) else "false"}"\n')
            f.write(f'AUTO_CAPITALIZE_MACRO="{"true" if cfg.get("auto_capitalize_macro", True) else "false"}"\n')
            f.write(f'PER_APP_REMEMBER="{"true" if cfg.get("per_app_remember", True) else "false"}"\n')
            f.write(f'AUTO_DISABLE_URL_BAR="{"true" if cfg.get("auto_disable_url_bar", True) else "false"}"\n')
            f.write(f'COMPACT_MODE="{"true" if cfg.get("compact_mode", True) else "false"}"\n')
            f.write(f'OUTPUT_MODE="{cfg.get("output_mode", "preedit")}"\n')
            f.write(f'IM_FRAMEWORK="{cfg.get("im_framework", "auto")}"\n')
            f.write(f'CHARSET="{cfg.get("charset", 0)}"\n')
            f.write(f'AUTOSTART="{"true" if cfg.get("autostart", True) else "false"}"\n')
            f.write(f'ICON_STYLE="{icon_style}"\n')
            f.write(f'FLAG_VARIANT="{flag_variant}"\n')
            f.write(f'RESTORE_KEY="{restore_key}"\n')
            f.write(f'THEME="{theme}"\n')
        _secure_file(CONFIG_ENV_FILE)
    except OSError:
        pass


def save_config(cfg: Dict[str, Any]) -> bool:
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
