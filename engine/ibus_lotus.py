#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ibus-lotus: Modern Vietnamese Input Method Engine for IBus (GNOME Wayland Native)
Powered by Lotus C++ Engine (bamboo-core)
"""

import os
import sys
import time
import subprocess
import ctypes
import gi

gi.require_version('IBus', '1.0')
from gi.repository import IBus, GLib, GObject

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from config.config_manager import load_config, save_config, CONFIG_FILE

SO_PATH = os.path.join(BASE_DIR, 'bridge', 'liblotus_bridge.so')
if not os.path.exists(SO_PATH):
    SO_PATH = "/usr/lib/ibus-lotus/liblotus_bridge.so"

bridge = ctypes.CDLL(SO_PATH)

bridge.lotus_bridge_create.restype = ctypes.c_void_p
bridge.lotus_bridge_create.argtypes = [ctypes.c_int, ctypes.c_uint32, ctypes.c_int]
bridge.lotus_bridge_free.argtypes = [ctypes.c_void_p]
bridge.lotus_bridge_reset.argtypes = [ctypes.c_void_p]
bridge.lotus_bridge_remove_last.argtypes = [ctypes.c_void_p]
bridge.lotus_bridge_set_flags.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
bridge.lotus_bridge_set_charset.argtypes = [ctypes.c_void_p, ctypes.c_int]
bridge.lotus_bridge_set_method.argtypes = [ctypes.c_void_p, ctypes.c_int]
bridge.lotus_bridge_get_full_string.restype = ctypes.c_int
bridge.lotus_bridge_get_full_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
bridge.lotus_bridge_feed_key.restype = ctypes.c_int
bridge.lotus_bridge_feed_key.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_int),
    ctypes.c_char_p,
    ctypes.c_size_t,
]
bridge.lotus_bridge_is_valid_word.restype = ctypes.c_int
bridge.lotus_bridge_is_valid_word.argtypes = [ctypes.c_void_p]

# Flag masks
FLAG_FREE_TONE = 1 << 0
FLAG_STD_TONE = 1 << 1
FLAG_AUTO_CORRECT = 1 << 2
FLAG_W2U = 1 << 3
FLAG_BRACKET = 1 << 4

PUNCTUATION_KEYVALS = {ord(c) for c in ",.;:/?!@#$%^&*()\'\"<>{}|\\~+-="}

QUICK_MENU_SCRIPT = os.path.join(BASE_DIR, 'ui', 'quick_menu.py')
SETUP_PANEL_SCRIPT = os.path.join(BASE_DIR, 'ui', 'setup_panel.py')

LOG_FILE = "/tmp/ibus_lotus.log"
def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

class IBusLotusEngine(IBus.Engine):
    __gtype_name__ = 'IBusLotusEngine'

    def __init__(self):
        super().__init__()
        log("Engine __init__ called")
        self.cfg = load_config()
        self.config_mtime = 0
        self._check_config_mtime()

        flags = self._compute_flags()
        charset = self.cfg.get("charset", 0)
        im = self.cfg.get("input_method", 0)

        self.handle = bridge.lotus_bridge_create(im, flags, charset)
        self.commit_buf = ctypes.create_string_buffer(512)
        self.full_buf = ctypes.create_string_buffer(512)
        self.del_cnt = ctypes.c_int(0)
        self.has_composition = False
        self.last_grave_time = 0
        self._client_caps = 0
        self.ctrl_pressed = False

    def _compute_flags(self):
        f = 0
        if self.cfg.get("free_tone_marking", True):
            f |= FLAG_FREE_TONE
        if not self.cfg.get("modern_tone_style", True):
            f |= FLAG_STD_TONE
        if self.cfg.get("auto_correct", True):
            f |= FLAG_AUTO_CORRECT
        if self.cfg.get("w2u", True):
            f |= FLAG_W2U
        if self.cfg.get("bracket_transform", True):
            f |= FLAG_BRACKET
        return f

    def _check_config_mtime(self):
        if os.path.exists(CONFIG_FILE):
            try:
                mtime = os.path.getmtime(CONFIG_FILE)
                if mtime > self.config_mtime:
                    self.config_mtime = mtime
                    return True
            except OSError:
                pass
        return False

    def reload_config(self):
        self.cfg = load_config()
        log(f"Config reloaded: output_mode={self.cfg.get('output_mode')}, enabled={self.cfg.get('enabled')}, im={self.cfg.get('input_method')}")
        if hasattr(self, 'handle') and self.handle:
            bridge.lotus_bridge_set_flags(self.handle, self._compute_flags())
            bridge.lotus_bridge_set_charset(self.handle, self.cfg.get("charset", 0))
            bridge.lotus_bridge_set_method(self.handle, self.cfg.get("input_method", 0))
            bridge.lotus_bridge_reset(self.handle)
        self.has_composition = False
        self._setup_properties()

    def _setup_properties(self):
        try:
            prop_list = IBus.PropList()
            is_vn = self.cfg.get("enabled", True)
            im = self.cfg.get("input_method", 0)
            im_name = "Telex" if im == 0 else ("VNI" if im == 1 else "Telex+VNI")
            lbl_text = f"VN ({im_name})" if is_vn else "EN (Tiếng Anh)"

            mode_prop = IBus.Property(
                key="LotusMode",
                prop_type=IBus.PropType.MENU,
                label=IBus.Text.new_from_string(lbl_text),
                icon=None,
                tooltip=IBus.Text.new_from_string("Bộ gõ tiếng Việt Lotus"),
                sensitive=True,
                visible=True,
                state=IBus.PropState.UNCHECKED,
                sub_props=None
            )

            sub_props = IBus.PropList()

            # Toggle VN/EN
            vn_item = IBus.Property(
                key="LotusToggleVN",
                prop_type=IBus.PropType.RADIO,
                label=IBus.Text.new_from_string("Tiếng Việt (Bật)"),
                sensitive=True,
                visible=True,
                state=IBus.PropState.CHECKED if is_vn else IBus.PropState.UNCHECKED
            )
            en_item = IBus.Property(
                key="LotusToggleEN",
                prop_type=IBus.PropType.RADIO,
                label=IBus.Text.new_from_string("Tiếng Anh (Tắt tiếng Việt)"),
                sensitive=True,
                visible=True,
                state=IBus.PropState.CHECKED if not is_vn else IBus.PropState.UNCHECKED
            )
            sub_props.append(vn_item)
            sub_props.append(en_item)

            # IM selection
            telex_item = IBus.Property(
                key="LotusIMTelex",
                prop_type=IBus.PropType.RADIO,
                label=IBus.Text.new_from_string("Kiểu gõ: Telex"),
                sensitive=True,
                visible=True,
                state=IBus.PropState.CHECKED if im == 0 else IBus.PropState.UNCHECKED
            )
            vni_item = IBus.Property(
                key="LotusIMVni",
                prop_type=IBus.PropType.RADIO,
                label=IBus.Text.new_from_string("Kiểu gõ: VNI"),
                sensitive=True,
                visible=True,
                state=IBus.PropState.CHECKED if im == 1 else IBus.PropState.UNCHECKED
            )
            sub_props.append(telex_item)
            sub_props.append(vni_item)

            # Settings launcher
            cfg_item = IBus.Property(
                key="LotusOpenSetup",
                prop_type=IBus.PropType.NORMAL,
                label=IBus.Text.new_from_string("⚙️ Bảng điều khiển (Unikey Style)..."),
                sensitive=True,
                visible=True
            )
            sub_props.append(cfg_item)

            mode_prop.set_sub_props(sub_props)
            prop_list.append(mode_prop)
            self.register_properties(prop_list)
        except Exception as e:
            log(f"Error in _setup_properties: {e}")

    def do_set_capabilities(self, caps):
        self._client_caps = caps
        log(f"do_set_capabilities: caps={caps} (has_surrounding={bool(caps & IBus.Capabilite.SURROUNDING_TEXT)}, has_preedit={bool(caps & IBus.Capabilite.PREEDIT_TEXT)})")

    def do_enable(self):
        log("do_enable called")
        self._check_and_reload()
        self._setup_properties()

    def do_disable(self):
        log("do_disable called")
        self._commit_and_reset()

    def do_focus_in(self):
        log("do_focus_in called")
        self._check_and_reload()
        self._setup_properties()
        self._commit_and_reset()

    def do_focus_out(self):
        log("do_focus_out called")
        self._commit_and_reset()

    def do_reset(self):
        log("do_reset called")
        self._commit_and_reset()

    def _check_and_reload(self):
        if self._check_config_mtime():
            self.reload_config()

    def do_property_activate(self, prop_name, state):
        if prop_name == "LotusToggleVN":
            self.cfg["enabled"] = True
            save_config(self.cfg)
            self.reload_config()
        elif prop_name == "LotusToggleEN":
            self.cfg["enabled"] = False
            save_config(self.cfg)
            self.reload_config()
        elif prop_name == "LotusIMTelex":
            self.cfg["input_method"] = 0
            save_config(self.cfg)
            self.reload_config()
        elif prop_name == "LotusIMVni":
            self.cfg["input_method"] = 1
            save_config(self.cfg)
            self.reload_config()
        elif prop_name == "LotusOpenSetup":
            subprocess.Popen([sys.executable, SETUP_PANEL_SCRIPT])

    def _open_quick_menu(self):
        try:
            subprocess.Popen([sys.executable, QUICK_MENU_SCRIPT])
        except Exception as e:
            log(f"Error opening quick menu: {e}")

    def do_process_key_event(self, keyval, keycode, state):
        try:
            return self._handle_key_event(keyval, keycode, state)
        except Exception as e:
            import traceback
            log(f"CRITICAL EXCEPTION in key_event: {e}\n{traceback.format_exc()}")
            return False

    def _handle_key_event(self, keyval, keycode, state):
        log(f"process_key_event: keyval={keyval} ({chr(keyval) if 0x20 <= keyval <= 0x7E else 'non-ascii'}), state={state}, enabled={self.cfg.get('enabled')}")

        # Track modifier presses
        is_press = not (state & IBus.ModifierType.RELEASE_MASK)

        # 1. Hotkey: Ctrl+Shift or Alt+Z to toggle Vietnamese/English (Unikey style)
        if is_press:
            # Check Alt+Z
            if (state & IBus.ModifierType.MOD1_MASK) and keyval in (IBus.KEY_z, IBus.KEY_Z):
                self.cfg["enabled"] = not self.cfg.get("enabled", True)
                save_config(self.cfg)
                self.reload_config()
                log(f"-> Hotkey Alt+Z: toggled enabled={self.cfg.get('enabled')}")
                return True

            # Check Ctrl+Shift (pressing Shift while Ctrl is held, or pressing Ctrl while Shift is held)
            if (keyval in (IBus.KEY_Shift_L, IBus.KEY_Shift_R) and (state & IBus.ModifierType.CONTROL_MASK)) or \
               (keyval in (IBus.KEY_Control_L, IBus.KEY_Control_R) and (state & IBus.ModifierType.SHIFT_MASK)):
                self.cfg["enabled"] = not self.cfg.get("enabled", True)
                save_config(self.cfg)
                self.reload_config()
                log(f"-> Hotkey Ctrl+Shift: toggled enabled={self.cfg.get('enabled')}")
                return True

        # Ignore key release events
        if state & IBus.ModifierType.RELEASE_MASK:
            return False

        # 2. Hotkey: Quick Menu Dialog on ` (grave)
        menu_key = self.cfg.get("mode_menu_key", "grave")
        if menu_key == "grave" and keyval == IBus.KEY_grave and not (state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK)):
            now = time.time()
            if (now - self.last_grave_time) < 0.4:
                self.last_grave_time = 0
                log("-> Double grave: passing through `")
                return False  # Pass through literal `
            self.last_grave_time = now
            if not self.has_composition:
                log("-> Opening quick menu")
                self._open_quick_menu()
                return True

        # If Vietnamese is disabled, pass all keys through
        if not self.cfg.get("enabled", True):
            return False

        # Pass through control shortcuts (Ctrl, Alt, Super) and reset composition
        if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK | IBus.ModifierType.SUPER_MASK):
            if self.has_composition:
                self._commit_and_reset()
            return False

        # Backspace handling
        if keyval == IBus.KEY_BackSpace:
            if self.has_composition:
                output_mode = self._get_effective_output_mode()
                bridge.lotus_bridge_remove_last(self.handle)
                full_len = bridge.lotus_bridge_get_full_string(self.handle, self.full_buf, ctypes.sizeof(self.full_buf))
                if full_len == 0:
                    self.has_composition = False
                    self.hide_preedit_text()
                    return True
                if output_mode == "preedit":
                    self._update_preedit(self.full_buf.value.decode('utf-8', 'ignore'))
                    return True
            return False

        # Word boundary keys: Space, Enter, Tab, Escape
        if keyval in (IBus.KEY_space, IBus.KEY_Return, IBus.KEY_KP_Enter, IBus.KEY_Tab, IBus.KEY_Escape):
            if self.has_composition:
                self._commit_and_reset()
            return False

        # Punctuation keys reset word composition
        if keyval in PUNCTUATION_KEYVALS:
            if self.has_composition:
                self._commit_and_reset()
            return False

        # Printable ASCII range
        if 0x20 <= keyval <= 0x7E:
            output_mode = self._get_effective_output_mode()
            self.del_cnt.value = 0
            log(f"-> Feeding key: keyval={keyval} ('{chr(keyval)}')")
            ok = bridge.lotus_bridge_feed_key(
                self.handle,
                keyval,
                ctypes.byref(self.del_cnt),
                self.commit_buf,
                ctypes.sizeof(self.commit_buf)
            )

            if ok:
                self.has_composition = True
                delete_n = self.del_cnt.value
                commit_text = self.commit_buf.value.decode('utf-8', 'ignore')
                log(f"-> feed_key ok: del={delete_n}, commit='{commit_text}', effective_mode={output_mode}")

                if output_mode == "preedit":
                    bridge.lotus_bridge_get_full_string(self.handle, self.full_buf, ctypes.sizeof(self.full_buf))
                    full_str = self.full_buf.value.decode('utf-8', 'ignore')
                    log(f"-> preedit update: '{full_str}'")
                    self._update_preedit(full_str)
                    return True

                elif output_mode == "forward":
                    for _ in range(delete_n):
                        self.forward_key_event(IBus.KEY_BackSpace, 0, 0)
                        self.forward_key_event(IBus.KEY_BackSpace, 0, IBus.ModifierType.RELEASE_MASK)
                    if commit_text:
                        self.commit_text(IBus.Text.new_from_string(commit_text))
                    return True

                else:
                    # Native Wayland Surrounding Text
                    if delete_n > 0:
                        log(f"-> calling delete_surrounding_text(-{delete_n}, {delete_n})")
                        self.delete_surrounding_text(-delete_n, delete_n)
                    if commit_text:
                        log(f"-> calling commit_text('{commit_text}')")
                        self.commit_text(IBus.Text.new_from_string(commit_text))
                    return True

        return False

    def _get_effective_output_mode(self):
        mode = self.cfg.get("output_mode", "preedit")
        # If surrounding text is configured but the client doesn't support it (e.g. Electron/Chromium caps=9):
        # Auto-fallback to preedit so characters are NEVER lost!
        if mode == "surrounding" and not (self._client_caps & IBus.Capabilite.SURROUNDING_TEXT):
            return "preedit"
        return mode

    def _update_preedit(self, text):
        if text:
            ib_text = IBus.Text.new_from_string(text)
            ib_text.append_attribute(IBus.AttrType.UNDERLINE, IBus.AttrUnderline.SINGLE, 0, len(text))
            self.update_preedit_text_with_mode(ib_text, len(text), True, IBus.PreeditFocusMode.COMMIT)
            self.show_preedit_text()
        else:
            self.hide_preedit_text()

    def _commit_and_reset(self):
        output_mode = self._get_effective_output_mode()
        if output_mode == "preedit" and self.has_composition:
            bridge.lotus_bridge_get_full_string(self.handle, self.full_buf, ctypes.sizeof(self.full_buf))
            full_str = self.full_buf.value.decode('utf-8', 'ignore')
            log(f"-> Committing preedit: '{full_str}'")
            if full_str:
                self.commit_text(IBus.Text.new_from_string(full_str))
            self.hide_preedit_text()

        bridge.lotus_bridge_reset(self.handle)
        self.has_composition = False

    def do_destroy(self):
        log("do_destroy called")
        if hasattr(self, 'handle') and self.handle:
            bridge.lotus_bridge_free(self.handle)
            self.handle = None

def main():
    IBus.init()
    bus = IBus.Bus()
    if not bus.is_connected():
        print("Error: Cannot connect to IBus daemon.", file=sys.stderr)
        sys.exit(1)

    factory = IBus.Factory.new(bus.get_connection())
    factory.add_engine("lotus", IBusLotusEngine)

    bus.request_name("org.freedesktop.IBus.Lotus", 0)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
