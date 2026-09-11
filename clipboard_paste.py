# VDI Clipboard Paste Module
# Pastes clipboard content character-by-character for VDI compatibility

import threading
import time

import pyperclip

from platform_utils import IS_LINUX
from settings import PASTE_MODES, config
from paste_text import prepare_vdi_text


class LinuxKeyboardAdapter:
    """Small keyboard-compatible facade backed by pynput on Linux/X11."""

    def __init__(self):
        self._controller = None
        self._keyboard_module = None

    def _ensure_runtime(self):
        if self._keyboard_module is None:
            from pynput import keyboard as pynput_keyboard

            self._keyboard_module = pynput_keyboard
            self._controller = pynput_keyboard.Controller()
        return self._keyboard_module, self._controller

    def _resolve_key(self, key):
        keyboard_module, _ = self._ensure_runtime()
        aliases = {
            "enter": keyboard_module.Key.enter,
            "tab": keyboard_module.Key.tab,
            "space": keyboard_module.Key.space,
            "home": keyboard_module.Key.home,
            "delete": keyboard_module.Key.delete,
            "backspace": keyboard_module.Key.backspace,
            "shift": keyboard_module.Key.shift,
            "ctrl": keyboard_module.Key.ctrl,
            "control": keyboard_module.Key.ctrl,
            "alt": keyboard_module.Key.alt,
            "escape": keyboard_module.Key.esc,
            "esc": keyboard_module.Key.esc,
            "win": keyboard_module.Key.cmd,
            "super": keyboard_module.Key.cmd,
        }
        return aliases.get(str(key).lower(), key)

    @staticmethod
    def _pynput_hotkey(hotkey):
        aliases = {
            "ctrl": "control",
            "escape": "esc",
            "win": "cmd",
            "super": "cmd",
        }
        parts = []
        for raw_part in hotkey.split("+"):
            part = aliases.get(raw_part.strip().lower(), raw_part.strip().lower())
            parts.append(f"<{part}>" if part in {"control", "shift", "alt", "cmd", "esc"} else part)
        return "+".join(parts)

    def add_hotkey(self, hotkey, callback):
        keyboard_module, _ = self._ensure_runtime()
        listener = keyboard_module.GlobalHotKeys({self._pynput_hotkey(hotkey): callback})
        listener.start()
        return listener

    @staticmethod
    def remove_hotkey(handle):
        handle.stop()

    def press(self, key):
        _, controller = self._ensure_runtime()
        controller.press(self._resolve_key(key))

    def release(self, key):
        _, controller = self._ensure_runtime()
        controller.release(self._resolve_key(key))

    def write(self, text, delay=0):
        _, controller = self._ensure_runtime()
        for character in text:
            controller.type(character)
            if delay:
                time.sleep(delay)


if IS_LINUX:
    keyboard = LinuxKeyboardAdapter()
else:
    import keyboard


class ClipboardPaste:
    """VDI-compatible clipboard paste utility."""

    SHIFT_CHARS = {
        "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
        "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
        "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\",
        ":": ";", '"': "'", "<": ",", ">": ".", "?": "/",
        "~": "`",
    }

    def __init__(self, on_status=None):
        self.on_status = on_status or (lambda msg, msg_type: print(msg))
        self._state_lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._paste_thread = None
        self.is_pasting = False
        self.hotkey = config.get("paste_hotkey", "ctrl+shift+v")
        self.pause_hotkey = config.get("pause_hotkey", "ctrl+shift+p")
        self.hotkey_handler = None
        self.pause_handler = None
        self.cancel_handler = None
        self.register_hotkeys()

    def register_hotkeys(self):
        """Register or refresh all global hotkeys used by the paste utility."""
        self.unregister_hotkeys()
        if self.pause_hotkey in {self.hotkey, "escape"}:
            self.on_status("Paste, pause, and cancel hotkeys must be different", "error")
            return False

        handles = []
        try:
            self.hotkey_handler = keyboard.add_hotkey(self.hotkey, self.trigger_paste)
            handles.append(self.hotkey_handler)
            self.pause_handler = keyboard.add_hotkey(self.pause_hotkey, self.pause_resume)
            handles.append(self.pause_handler)
            self.cancel_handler = keyboard.add_hotkey("escape", self.cancel_paste)
            handles.append(self.cancel_handler)
        except Exception as exc:
            for handle in handles:
                try:
                    keyboard.remove_hotkey(handle)
                except Exception:
                    pass
            self.hotkey_handler = None
            self.pause_handler = None
            self.cancel_handler = None
            self.on_status(f"Paste hotkey registration failed: {exc}", "error")
            return False
        return True

    def unregister_hotkeys(self):
        """Remove registered global hotkeys."""
        try:
            if self.hotkey_handler is not None:
                keyboard.remove_hotkey(self.hotkey_handler)
                self.hotkey_handler = None
        except Exception:
            pass
        try:
            if self.pause_handler is not None:
                keyboard.remove_hotkey(self.pause_handler)
                self.pause_handler = None
        except Exception:
            pass
        try:
            if self.cancel_handler is not None:
                keyboard.remove_hotkey(self.cancel_handler)
                self.cancel_handler = None
        except Exception:
            pass

    def trigger_paste(self, content=None):
        """Start a paste operation if one is not already running."""
        with self._state_lock:
            if self.is_pasting:
                already_running = True
            else:
                already_running = False
                self.is_pasting = True
                self._cancel_event.clear()
                self._pause_event.clear()
                self._paste_thread = threading.Thread(
                    target=self._paste,
                    args=(content,),
                    daemon=True,
                )
                paste_thread = self._paste_thread

        if already_running:
            self.on_status("Paste already running", "warning")
            return False

        self.on_status(f"Paste triggered ({self.hotkey.upper()})", "info")
        try:
            paste_thread.start()
        except Exception:
            with self._state_lock:
                self.is_pasting = False
                self._paste_thread = None
            raise
        return True

    def cancel_paste(self):
        """Cancel the active paste operation."""
        with self._state_lock:
            if not self.is_pasting:
                return False
            self._cancel_event.set()
            self._pause_event.clear()
        self.on_status("Paste cancellation requested", "warning")
        return True

    def pause_resume(self):
        """Pause an active paste or resume it when paused."""
        with self._state_lock:
            if not self.is_pasting:
                return False
            if self._pause_event.is_set():
                self._pause_event.clear()
                message = "Paste resumed"
            else:
                self._pause_event.set()
                message = "Paste paused"
        self.on_status(message, "info")
        return True

    def get_status(self):
        with self._state_lock:
            if not self.is_pasting:
                return "Ready"
            if self._pause_event.is_set():
                return "Paused"
            return "Pasting"

    def _press_key(self, key, press_duration, needs_shift=False):
        self._neutralize_modifiers()
        if needs_shift:
            keyboard.press("shift")
            self._cancel_event.wait(max(0.01, min(press_duration, 0.03)))
        try:
            keyboard.press(key)
            self._cancel_event.wait(press_duration)
            keyboard.release(key)
        finally:
            if needs_shift:
                self._release_modifier("shift")
                self._cancel_event.wait(max(press_duration, 0.03))

    @staticmethod
    def _release_modifier(modifier):
        # Remote clients can occasionally miss or defer one modifier-up event.
        # Repeating it establishes a known state before the next character.
        for _ in range(2):
            try:
                keyboard.release(modifier)
            except Exception:
                pass

    def _neutralize_modifiers(self):
        for modifier in ("shift", "ctrl", "alt"):
            self._release_modifier(modifier)
        self._cancel_event.wait(0.01)

    def _clear_generated_indent(self, press_duration):
        # Shift+Home selects only whitespace inserted by the editor after Enter.
        # Delete is harmless when the new line already begins at column zero.
        self._press_key("home", press_duration, needs_shift=True)
        self._press_key("delete", press_duration)

    def _type_char(self, char, press_duration):
        if char == "\n":
            self._press_key("enter", press_duration)
            self._cancel_event.wait(max(config.get("char_delay", 0.05), 0.04))
            if not self._cancel_event.is_set():
                self._clear_generated_indent(press_duration)
            return
        if char == "\t":
            self._press_key("tab", press_duration)
            return
        if char == " ":
            self._press_key("space", press_duration)
            return
        if char.isascii() and char.isupper() and char.isalpha():
            self._press_key(char.lower(), press_duration, needs_shift=True)
            return
        if char in self.SHIFT_CHARS:
            self._press_key(self.SHIFT_CHARS[char], press_duration, needs_shift=True)
            return
        if char.isascii() and char.isprintable():
            self._press_key(char, press_duration)
            return

        # Unsupported Unicode is removed before typing. Never inject a partial
        # remote Unicode sequence that may leave modifiers active.
        return

    def _paste(self, content_override=None):
        content = ""
        try:
            content = pyperclip.paste() if content_override is None else str(content_override)
            if not content:
                self.on_status("Clipboard empty", "warning")
                return

            if config.get("trim_trailing_whitespace", True):
                content = content.rstrip()
            content, skipped = prepare_vdi_text(content)
            if skipped:
                self.on_status(f"Skipping {skipped} unsupported symbols; remaining text will be pasted", "warning")
            if not content:
                self.on_status("Clipboard contains no sendable text", "warning")
                return

            char_delay = config.get("char_delay", 0.05)
            press_duration = config.get("press_duration", 0.02)

            self.on_status(f"Pasting {len(content)} chars...", "info")
            if self._cancel_event.wait(0.3):
                self.on_status("Paste cancelled before typing", "warning")
                return

            progress_interval = max(1, len(content) // 20)

            for index, char in enumerate(content):
                if self._cancel_event.is_set():
                    self.on_status(f"Paste cancelled at {index}/{len(content)}", "warning")
                    return

                while self._pause_event.is_set() and not self._cancel_event.is_set():
                    self._cancel_event.wait(0.05)

                if self._cancel_event.is_set():
                    self.on_status(f"Paste cancelled at {index}/{len(content)}", "warning")
                    return

                if char == "\r":
                    if index + 1 < len(content) and content[index + 1] == "\n":
                        continue
                    char = "\n"

                self._type_char(char, press_duration)

                if (index + 1) % progress_interval == 0 or index == len(content) - 1:
                    self.on_status(f"Paste progress: {index + 1}/{len(content)}", "progress")

                if self._cancel_event.wait(char_delay):
                    self.on_status(f"Paste cancelled at {index + 1}/{len(content)}", "warning")
                    return

            self.on_status(
                f"Paste complete; skipped {skipped} unsupported symbols" if skipped else "Paste complete!",
                "warning" if skipped else "success",
            )

        except Exception as exc:
            self.on_status(f"Paste error: {exc}", "error")
        finally:
            with self._state_lock:
                self.is_pasting = False
                self._pause_event.clear()
                self._paste_thread = None

    def set_mode(self, mode):
        config.apply_paste_mode(mode)
        delays = PASTE_MODES.get(mode, PASTE_MODES["safe"])
        self.on_status(f"Mode: {mode} ({delays['char_delay'] * 1000:.0f}ms)", "info")

    def get_mode(self):
        return config.get("paste_mode", "safe")

    def set_hotkey(self, hotkey):
        if not hotkey:
            return
        config.set("paste_hotkey", hotkey)
        self.hotkey = config.get("paste_hotkey", hotkey)
        self.register_hotkeys()
        self.on_status(f"Paste hotkey set to {self.hotkey.upper()}", "info")

    def set_pause_hotkey(self, hotkey):
        if not hotkey:
            return
        config.set("pause_hotkey", hotkey)
        self.pause_hotkey = config.get("pause_hotkey", hotkey)
        self.register_hotkeys()
        self.on_status(f"Pause hotkey set to {self.pause_hotkey.upper()}", "info")

    def update_settings(
        self,
        *,
        mode=None,
        char_delay=None,
        press_duration=None,
        hotkey=None,
        pause_hotkey=None,
        trim_trailing_whitespace=None,
    ):
        updates = {}
        if mode is not None:
            if mode not in PASTE_MODES:
                raise ValueError(f"Invalid paste mode: {mode}")
            updates["paste_mode"] = mode
            if char_delay is None:
                updates["char_delay"] = PASTE_MODES[mode]["char_delay"]
            if press_duration is None:
                updates["press_duration"] = PASTE_MODES[mode]["press_duration"]
        if char_delay is not None:
            updates["char_delay"] = char_delay
        if press_duration is not None:
            updates["press_duration"] = press_duration
        if hotkey is not None:
            updates["paste_hotkey"] = hotkey
        if pause_hotkey is not None:
            updates["pause_hotkey"] = pause_hotkey
        if trim_trailing_whitespace is not None:
            updates["trim_trailing_whitespace"] = trim_trailing_whitespace

        if updates:
            config.update(updates)
            self.hotkey = config.get("paste_hotkey", self.hotkey)
            self.pause_hotkey = config.get("pause_hotkey", self.pause_hotkey)
            self.register_hotkeys()

        if mode is not None:
            self.on_status(f"Mode: {mode} ({config.get('char_delay') * 1000:.0f}ms)", "info")

    def reload_from_config(self):
        self.hotkey = config.get("paste_hotkey", self.hotkey)
        self.pause_hotkey = config.get("pause_hotkey", self.pause_hotkey)
        self.register_hotkeys()

    def cleanup(self):
        self.cancel_paste()
        self.unregister_hotkeys()
        with self._state_lock:
            paste_thread = self._paste_thread
        if paste_thread and paste_thread is not threading.current_thread():
            paste_thread.join(timeout=2)
