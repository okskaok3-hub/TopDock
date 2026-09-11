# Auto Clicker Module
# Clicks within a selected area at configurable intervals

import random
import threading
import time
import tkinter as tk

import pyautogui
from pynput import keyboard as pynput_keyboard

from settings import config


class AutoClicker:
    """Auto clicker with area selection."""

    def __init__(self, root, on_status=None, dispatch=None, is_target_active=None):
        self.root = root
        self.on_status = on_status or (lambda msg, msg_type: print(msg))
        self.dispatch = dispatch or (lambda callback: root.after(0, callback))
        self.is_target_active = is_target_active

        saved_area = config.get("click_area", [])
        self.selection_coords = tuple(saved_area) if len(saved_area) == 4 else None
        self.clicking = False
        self.program_running = True
        self.selection_window = None
        self.status_window = None

        self.delay_min = config.get("click_delay_min", 60.0)
        self.delay_max = config.get("click_delay_max", 60.0)
        self.hotkey = config.get("clicker_hotkey", "shift+alt+9")

        self.listener = None
        self.click_thread = None

    def select_area(self):
        """Show fullscreen area selection UI."""
        self.on_status("Select click area...", "info")

        self.selection_window = tk.Toplevel(self.root)
        self.selection_window.attributes("-fullscreen", True)
        self.selection_window.attributes("-alpha", 0.3)
        self.selection_window.attributes("-topmost", True)
        self.selection_window.configure(background="grey")

        self.canvas = tk.Canvas(
            self.selection_window,
            cursor="cross",
            bg="grey",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.select_label = tk.Label(
            self.selection_window,
            text="Click and drag to select the area. Release to confirm.",
            font=("Segoe UI", 20),
            fg="white",
            bg="grey",
        )
        self.select_label.place(relx=0.5, rely=0.1, anchor="center")

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.selection_window.bind("<Escape>", self._cancel_selection)
        self.selection_window.focus_force()

    def _cancel_selection(self, _event=None):
        if self.selection_window:
            self.selection_window.destroy()
            self.selection_window = None
        self.on_status("Area selection cancelled", "info")

    def _on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="#7c3aed",
            width=3,
        )

    def _on_mouse_drag(self, event):
        if self.rect:
            self.canvas.coords(
                self.rect,
                self.start_x,
                self.start_y,
                event.x,
                event.y,
            )

    def _on_mouse_up(self, event):
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        if x2 - x1 < 10 or y2 - y1 < 10:
            self.on_status("Selection too small!", "warning")
            self.selection_window.destroy()
            return

        self.selection_coords = (x1, y1, x2, y2)
        config.set("click_area", list(self.selection_coords))

        self.canvas.destroy()
        self.select_label.destroy()
        self.selection_window.destroy()
        self.selection_window = None

        self.on_status(f"Area selected: {x2 - x1}x{y2 - y1}px", "success")
        print(f"Area selected: {self.selection_coords}")
        print(f"Press {self.hotkey.upper()} to TOGGLE clicking.")
        print("Press ESC to stop clicking.")

        self._setup_status_overlay()
        self.ensure_runtime()

    def _setup_status_overlay(self):
        if self.status_window:
            try:
                self.status_window.destroy()
            except Exception:
                pass

        self.status_window = tk.Toplevel(self.root)
        self.status_window.overrideredirect(True)
        self.status_window.attributes("-topmost", True)
        self.status_window.attributes("-alpha", 0.85)
        self.status_window.configure(bg="#1a1a2e")

        screen_width = self.status_window.winfo_screenwidth()
        self.status_window.geometry(f"220x50+{screen_width - 240}+20")

        self.status_label = tk.Label(
            self.status_window,
            text="Clicker: READY",
            fg="#10b981",
            bg="#1a1a2e",
            font=("Segoe UI", 11, "bold"),
        )
        self.status_label.pack(expand=True, fill="both")
        self.status_window.withdraw()

    def ensure_runtime(self):
        """Ensure the click thread and listener are running."""
        if not self.click_thread or not self.click_thread.is_alive():
            self.click_thread = threading.Thread(target=self._click_loop, daemon=True)
            self.click_thread.start()
        self.start_listener()

    def start_listener(self):
        """Start or refresh the clicker hotkey listener."""
        self.stop_listener()
        try:
            self.listener = pynput_keyboard.GlobalHotKeys(self._get_hotkey_map())
            self.listener.start()
        except Exception as exc:
            self.listener = None
            self.on_status(f"Clicker hotkey registration failed: {exc}", "error")

    def stop_listener(self):
        """Stop the clicker hotkey listener."""
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None

    def _click_loop(self):
        print(f"Clicker thread started. Waiting for {self.hotkey.upper()}...")

        while self.program_running:
            if self.clicking and self.selection_coords:
                if self.is_target_active and not self.is_target_active():
                    time.sleep(0.25)
                    continue

                x1, y1, x2, y2 = self.selection_coords
                target_x = random.randint(x1, x2)
                target_y = random.randint(y1, y2)

                try:
                    pyautogui.click(target_x, target_y)
                    delay = random.uniform(self.delay_min, self.delay_max)
                    time.sleep(delay)
                except Exception as exc:
                    print(f"Click error: {exc}")
                    self.clicking = False
                    self.on_status(f"Clicker stopped after click error: {exc}", "error")
                    time.sleep(0.2)
            else:
                time.sleep(0.1)

    def toggle(self):
        """Toggle clicking on or off."""
        if not self.selection_coords and not self.clicking:
            self.on_status("Select an area first", "warning")
            return False

        if self.clicking:
            print("Paused clicking.")
            self.clicking = False
            self.on_status("Clicker: PAUSED", "info")
            if self.status_window:
                self.status_window.after(
                    0,
                    lambda: self.status_label.config(text="Clicker: PAUSED", fg="#fbbf24"),
                )
                self.status_window.after(2000, self.status_window.withdraw)
        else:
            print("Started clicking!")
            self.clicking = True
            self.on_status("Clicker: RUNNING", "success")
            if self.status_window:
                self.status_window.after(
                    0,
                    lambda: (
                        self.status_label.config(text="Clicker: RUNNING", fg="#ef4444"),
                        self.status_window.deiconify(),
                    ),
                )
        return self.clicking

    def handle_escape(self):
        """Stop active clicking without tearing down the clicker."""
        if self.clicking:
            print("Stopping clicker...")
            self.clicking = False
            self.on_status("Clicker stopped", "info")
            if self.status_window:
                self.status_window.after(0, self.status_window.withdraw)
            return True
        return False

    def start(self):
        """Start clicking when an area has been configured."""
        if self.selection_coords and not self.clicking:
            return self.toggle()
        return self.clicking

    def stop(self):
        """Stop clicking."""
        was_running = self.clicking
        self.clicking = False
        if self.status_window:
            self.status_window.after(0, self.status_window.withdraw)
        return was_running

    def get_status(self):
        if self.clicking:
            return "Running"
        if self.selection_coords:
            return "Ready"
        return "No Area"

    def _get_hotkey_map(self):
        return {
            self._to_pynput_hotkey(self.hotkey): self._dispatch_toggle,
            "<esc>": self._dispatch_escape,
        }

    def _dispatch_toggle(self):
        """Move hotkey callbacks from pynput's thread onto Tk's UI thread."""
        self.dispatch(self.toggle)

    def _dispatch_escape(self):
        """Move Escape handling from pynput's thread onto Tk's UI thread."""
        self.dispatch(self.handle_escape)

    def _to_pynput_hotkey(self, hotkey):
        parts = [part.strip().lower() for part in hotkey.split("+") if part.strip()]
        mapped = []
        for part in parts:
            if part in ("shift", "alt", "ctrl", "control", "cmd", "win", "super"):
                key = "control" if part == "ctrl" else part
                mapped.append(f"<{key}>")
            else:
                mapped.append(part)
        return "+".join(mapped)

    def set_hotkey(self, hotkey):
        if not hotkey:
            return
        config.set("clicker_hotkey", hotkey)
        self.hotkey = config.get("clicker_hotkey", hotkey)
        self.start_listener()
        self.on_status(f"Clicker hotkey set to {self.hotkey.upper()}", "info")

    def set_delays(self, delay_min, delay_max):
        config.update({
            "click_delay_min": delay_min,
            "click_delay_max": delay_max,
        })
        self.delay_min = config.get("click_delay_min", delay_min)
        self.delay_max = config.get("click_delay_max", delay_max)

    def update_settings(self, *, hotkey=None, delay_min=None, delay_max=None):
        updates = {}
        if hotkey is not None:
            updates["clicker_hotkey"] = hotkey
        if delay_min is not None:
            updates["click_delay_min"] = delay_min
        if delay_max is not None:
            updates["click_delay_max"] = delay_max
        if updates:
            config.update(updates)
            self.reload_from_config()
            if hotkey is not None:
                self.on_status(f"Clicker hotkey set to {self.hotkey.upper()}", "info")

    def reload_from_config(self):
        self.hotkey = config.get("clicker_hotkey", self.hotkey)
        self.delay_min = config.get("click_delay_min", self.delay_min)
        self.delay_max = config.get("click_delay_max", self.delay_max)
        self.start_listener()

    def cleanup(self):
        self.program_running = False
        self.clicking = False
        self.stop_listener()

        if self.status_window:
            try:
                self.status_window.destroy()
            except Exception:
                pass

        if self.selection_window:
            try:
                self.selection_window.destroy()
            except Exception:
                pass
