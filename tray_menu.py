# Unified System Tray Menu
# Single tray icon with submenus for all tools
# Cross-platform: Windows and Linux

from PIL import Image, ImageDraw
import pystray
from pystray import Menu, MenuItem as Item

from platform_utils import IS_LINUX, is_in_startup, toggle_startup
from settings import config


class TrayMenu:
    """Unified system tray menu for VDI Toolkit."""

    def __init__(self, clipboard, clicker, ai_assistant, ui, notifier, on_exit, dispatch=None):
        self.clipboard = clipboard
        self.clicker = clicker
        self.ai_assistant = ai_assistant
        self.ui = ui
        self.notifier = notifier
        self.on_exit = on_exit
        self.dispatch = dispatch or (lambda callback: ui.root.after(0, callback))
        self.icon = None
        self._create()

    def _create(self):
        image = self._create_icon()

        menu = Menu(
            Item("VDI Toolkit", None, enabled=False),
            Item("Open Control Center", self._open_control_center),
            Menu.SEPARATOR,
            Item("Clipboard Paste", Menu(
                Item("Paste Now", self._paste_now),
                Item("Pause / Resume", self._pause_resume_paste),
                Item("Cancel Paste", self._cancel_paste),
                Menu.SEPARATOR,
                Item("Fast Mode", self._set_fast, checked=lambda item: config.get("paste_mode") == "fast"),
                Item("Safe Mode", self._set_safe, checked=lambda item: config.get("paste_mode") == "safe"),
                Item("Ultra-Safe", self._set_ultra, checked=lambda item: config.get("paste_mode") == "ultra_safe"),
                Menu.SEPARATOR,
                Item(
                    lambda item: f"Hotkey: {config.get('paste_hotkey').upper()}",
                    None,
                    enabled=False,
                ),
            )),
            Item("Auto Clicker", Menu(
                Item("Select Area...", self._select_area),
                Item("Start/Stop", self._toggle_clicker),
                Menu.SEPARATOR,
                Item(
                    lambda item: f"Hotkey: {config.get('clicker_hotkey').upper()}",
                    None,
                    enabled=False,
                ),
            )),
            Item("AI Screenshot", Menu(
                Item("Capture && Ask", self._capture_ai),
                Item("Settings...", self._open_ai_settings),
                Menu.SEPARATOR,
                Item(
                    lambda item: f"Provider: {config.get('ai_provider').upper()}",
                    None,
                    enabled=False,
                ),
                Item(
                    lambda item: f"Hotkey: {config.get('ai_hotkey').upper()}",
                    None,
                    enabled=False,
                ),
            )),
            Item("Notifications", Menu(
                Item("Enabled", self._toggle_notify, checked=lambda item: self.notifier.enabled),
                Item(
                    "Float over full-screen VDI",
                    self._toggle_overlay,
                    checked=lambda item: self.notifier.overlay_enabled,
                ),
                Item("Clear All", self._clear_notify),
                Item("Test", self._test_notify),
            )),
            Menu.SEPARATOR,
            Item(
                "Start with Linux" if IS_LINUX else "Start with Windows",
                toggle_startup,
                checked=lambda item: is_in_startup(),
            ),
            Menu.SEPARATOR,
            Item("Exit", self._exit),
        )

        self.icon = pystray.Icon("vdi_toolkit", image, "VDI Toolkit", menu)

    def _create_icon(self, size=64):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, size - 4, size - 4], fill=(124, 58, 237))

        cx, cy = size // 2, size // 2
        draw.polygon([
            (cx - 12, cy - 8),
            (cx, cy + 10),
            (cx + 12, cy - 8),
            (cx + 8, cy - 8),
            (cx, cy + 2),
            (cx - 8, cy - 8),
        ], fill=(255, 255, 255))

        return img

    def _set_fast(self, icon, item):
        self._run_on_ui(lambda: self._set_mode("fast", "20ms delay"))

    def _set_safe(self, icon, item):
        self._run_on_ui(lambda: self._set_mode("safe", "50ms delay"))

    def _set_ultra(self, icon, item):
        self._run_on_ui(lambda: self._set_mode("ultra_safe", "100ms delay"))

    def _run_on_ui(self, callback):
        """Run callbacks that touch Tk or shared runtime state on the UI thread."""
        self.dispatch(callback)

    def _set_mode(self, mode, description):
        self.clipboard.set_mode(mode)
        self.notifier.show("Paste", f"{mode.replace('_', ' ').title()} Mode", description)

    def _paste_now(self, icon=None, item=None):
        self._run_on_ui(self.clipboard.trigger_paste)

    def _pause_resume_paste(self, icon=None, item=None):
        self._run_on_ui(self.clipboard.pause_resume)

    def _cancel_paste(self, icon=None, item=None):
        self._run_on_ui(self.clipboard.cancel_paste)

    def _select_area(self, icon=None, item=None):
        self._run_on_ui(self.clicker.select_area)

    def _toggle_clicker(self, icon=None, item=None):
        self._run_on_ui(self.clicker.toggle)

    def _capture_ai(self, icon=None, item=None):
        self._run_on_ui(self.ai_assistant.capture_and_ask)

    def _open_ai_settings(self, icon=None, item=None):
        self._run_on_ui(self.ai_assistant.open_settings_dialog)

    def _open_control_center(self, icon=None, item=None):
        self._run_on_ui(self.ui.show_window)

    def _toggle_notify(self, icon, item):
        self._run_on_ui(self._toggle_notifications)

    def _toggle_notifications(self):
        enabled = self.notifier.toggle()
        self.notifier.show("Notifications", "Enabled" if enabled else "Disabled")

    def _toggle_overlay(self, icon, item):
        self._run_on_ui(self._toggle_overlay_on_ui)

    def _toggle_overlay_on_ui(self):
        enabled = not self.notifier.overlay_enabled
        self.notifier.set_overlay(enabled)
        self.notifier.show(
            "Notifications",
            "Overlay enabled" if enabled else "Overlay disabled",
            "Cards will float above full-screen VDI windows."
            if enabled else "Cards use normal window ordering.",
        )

    def _clear_notify(self, icon=None, item=None):
        self._run_on_ui(self.notifier.clear_all)

    def _test_notify(self, icon=None, item=None):
        self._run_on_ui(
            lambda: self.notifier.show("VDI Toolkit", "Test Notification", "Everything is working!")
        )

    def _exit(self, icon=None, item=None):
        if self.icon:
            self.icon.stop()
        self._run_on_ui(self.on_exit)

    def run(self):
        self.icon.run()

    def stop(self):
        if self.icon:
            self.icon.stop()
