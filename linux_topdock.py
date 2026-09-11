#!/usr/bin/env python3
"""Premium auto-hiding TopDock for Linux/X11 VDI workflows."""

from datetime import datetime
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from queue import SimpleQueue, Empty

from linux_screenshot_service import LinuxScreenshotService
from linux_window_service import X11WindowService
from platform_utils import IS_LINUX, get_linux_runtime_warnings, is_in_startup, toggle_startup
from startup_diagnostics import check_required_modules, print_startup_report


class LinuxTopDock:
    TITLE = "TopDock Linux"
    HEIGHT = 76
    EDGE_HEIGHT = 4

    COLORS = {
        "background": "#15171d",
        "surface": "#20232b",
        "surface_hover": "#292d37",
        "border": "#323744",
        "text": "#f7f8fa",
        "muted": "#a6adbb",
        "primary": "#a855f7",
        "primary_dark": "#6d28d9",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    }

    def __init__(self, root):
        self.root = root
        self.window_service = X11WindowService(self.TITLE)
        self.width = max(1, min(1500, root.winfo_screenwidth() - 16))
        self.x = max(0, (root.winfo_screenwidth() - self.width) // 2)
        self.shown_y = 0
        self.hidden_y = -(self.HEIGHT - self.EDGE_HEIGHT)
        self.is_shown = True
        self.pinned = False
        self.last_inside = time.monotonic()
        self.animation_id = None
        self.status_until = 0.0
        self.hotkey_listener = None
        self.windows = []
        self.screenshot_window = None
        self.capture_busy = False
        self.settings_window = None
        self.ui_queue = SimpleQueue()
        self.card_slots = []

        self._configure_window()
        self._build_ui()
        for number in range(1, 10):
            self.root.bind_all(
                f"<Alt-Key-{number}>",
                lambda _event, index=number - 1: self._activate_visible_index(index),
            )

        from auto_clicker import AutoClicker
        from clipboard_paste import ClipboardPaste

        self.clipboard = ClipboardPaste(on_status=self._module_status)
        self.screenshot_service = LinuxScreenshotService()
        self.clicker = AutoClicker(
            root,
            on_status=self._module_status,
            dispatch=self.ui_queue.put,
            is_target_active=self.window_service.is_vdi_active,
        )
        self._start_reveal_hotkey()

        self.root.protocol("WM_DELETE_WINDOW", self.exit)
        self.root.after(100, self._finish_window_setup)
        self.root.after(120, self._track_pointer)
        self.root.after(250, self._refresh_windows)
        self.root.after(1000, self._update_clock)
        self.root.after(1500, self._reassert_overlay)
        self.root.after(50, self._drain_ui_queue)

        warnings = get_linux_runtime_warnings()
        if warnings:
            self._set_status(warnings[0], "warning", duration=8000)

    def _configure_window(self):
        self.root.title(self.TITLE)
        self.root.overrideredirect(True)
        self.root.configure(bg=self.COLORS["background"])
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", 0.985)
        except tk.TclError:
            pass
        self._set_geometry(self.shown_y)

    def _build_ui(self):
        outer = tk.Frame(
            self.root,
            bg=self.COLORS["background"],
            highlightbackground=self.COLORS["border"],
            highlightthickness=1,
        )
        outer.pack(fill="both", expand=True)

        content = tk.Frame(outer, bg=self.COLORS["background"])
        content.pack(fill="both", expand=True, padx=12, pady=8)
        content.grid_columnconfigure(2, weight=1)
        content.grid_rowconfigure(0, weight=1)

        brand = tk.Frame(content, bg=self.COLORS["background"], width=158)
        brand.grid(row=0, column=0, sticky="ns")
        brand.pack_propagate(False)

        logo = tk.Label(
            brand,
            text="Λ",
            bg=self.COLORS["primary"],
            fg="white",
            font=("Inter", 20, "bold"),
            width=2,
            height=1,
        )
        logo.pack(side="left", padx=(0, 8))

        brand_text = tk.Frame(brand, bg=self.COLORS["background"])
        brand_text.pack(side="left", fill="y")
        tk.Label(
            brand_text,
            text="TOPDOCK",
            bg=self.COLORS["background"],
            fg=self.COLORS["text"],
            font=("Inter", 10, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))
        self.status_label = tk.Label(
            brand_text,
            text="Linux · Ready",
            bg=self.COLORS["background"],
            fg=self.COLORS["muted"],
            font=("Inter", 8),
            anchor="w",
        )
        self.status_label.pack(anchor="w", pady=(3, 0))

        tk.Frame(content, bg=self.COLORS["border"], width=1).grid(row=0, column=1, sticky="ns", pady=8)

        center = tk.Frame(content, bg=self.COLORS["background"])
        center.grid(row=0, column=2, sticky="nsew", padx=10)
        center.grid_columnconfigure(0, weight=1)
        self.window_canvas = tk.Canvas(
            center,
            bg=self.COLORS["background"],
            height=44,
            width=1,
            highlightthickness=0,
            bd=0,
        )
        self.window_canvas.grid(row=0, column=0, sticky="ew")
        self.window_frame = tk.Frame(self.window_canvas, bg=self.COLORS["background"])
        self.window_canvas_item = self.window_canvas.create_window(
            0, 0, window=self.window_frame, anchor="nw"
        )
        self.window_scrollbar = tk.Canvas(center, height=12, width=1,
            bg=self.COLORS["background"], highlightthickness=0, cursor="sb_h_double_arrow", takefocus=True)
        self.window_scrollbar.grid(row=1, column=0, sticky="ew")
        self.window_canvas.configure(xscrollcommand=self._draw_slider)
        self.window_scrollbar.bind("<Configure>", lambda _e: self._draw_slider(*self.window_canvas.xview()))
        self.window_scrollbar.bind("<Button-1>", self._slider_press)
        self.window_scrollbar.bind("<B1-Motion>", self._slider_drag)
        self.window_scrollbar.bind("<Left>", lambda _e: self._scroll_windows(-3))
        self.window_scrollbar.bind("<Right>", lambda _e: self._scroll_windows(3))
        self.window_canvas.bind("<Configure>", self._resize_window_strip)
        self.window_canvas.bind("<Button-4>", lambda _event: self._scroll_windows(-3))
        self.window_canvas.bind("<Button-5>", lambda _event: self._scroll_windows(3))
        self.window_count_label = tk.Label(
            center,
            text="Discovering applications…",
            bg=self.COLORS["background"],
            fg=self.COLORS["muted"],
            font=("Inter", 7),
        )

        tk.Frame(content, bg=self.COLORS["border"], width=1).grid(row=0, column=3, sticky="ns", pady=8)

        tools = tk.Frame(content, bg=self.COLORS["background"])
        tools.grid(row=0, column=4, sticky="n", padx=(8, 0))

        self.paste_button = self._tool_button(tools, "⎘\nPASTE", self.paste_clipboard, width=7)
        self.shot_button = self._tool_button(tools, "⌖\nSHOT", self.select_screenshot_area, width=6)
        self.auto_button = self._tool_button(tools, "◎\nAUTO OFF", self.toggle_clicker, width=8)
        self.area_button = self._tool_button(tools, "⚙\nAREA", self.select_click_area, width=6)
        self.startup_button = self._tool_button(tools, "START", self.toggle_startup, width=7)
        self.pin_button = self._tool_button(tools, "PIN", self.toggle_pin, width=5)
        self._tool_button(tools, "⚙\nSETTINGS", self.show_settings, width=7)
        self._update_control_states()

    def _separator(self, parent):
        tk.Frame(parent, bg=self.COLORS["border"], width=1).pack(
            side="left", fill="y", padx=3, pady=3
        )

    def _tool_button(self, parent, text, command, width=7, danger=False):
        normal = self.COLORS["surface"]
        hover = "#3a242b" if danger else self.COLORS["surface_hover"]
        shell = tk.Frame(parent, width=64 if width >= 7 else 52, height=44,
                         bg=self.COLORS["background"])
        shell.pack(side="left", padx=3)
        shell.pack_propagate(False)
        button = tk.Button(
            shell,
            text=text,
            command=command,
            bg=normal,
            fg=self.COLORS["danger"] if danger else self.COLORS["text"],
            activebackground=hover,
            activeforeground=self.COLORS["text"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            highlightcolor=self.COLORS["primary"],
            font=("Inter", 8, "bold"),
            cursor="hand2",
            takefocus=True,
        )
        button.pack(fill="both", expand=True)
        button.bind("<Enter>", lambda _event: button.configure(bg=hover))
        button.bind("<Leave>", lambda _event: button.configure(bg=normal))
        return button

    def _finish_window_setup(self):
        self.root.lift()
        self.window_service.apply_overlay_hints(self.root.winfo_id())

    def _reassert_overlay(self):
        if self.capture_busy:
            self.root.after(2500, self._reassert_overlay)
            return
        try:
            self.root.attributes("-topmost", True)
            self.root.lift()
            self.window_service.apply_overlay_hints(self.root.winfo_id())
        except tk.TclError:
            return
        self.root.after(2500, self._reassert_overlay)

    def _start_reveal_hotkey(self):
        try:
            from pynput import keyboard as pynput_keyboard

            self.hotkey_listener = pynput_keyboard.GlobalHotKeys({
                "<ctrl>+<alt>+<space>": lambda: self.ui_queue.put(self.reveal)
            })
            self.hotkey_listener.start()
        except Exception as exc:
            self._set_status(f"Reveal hotkey unavailable: {exc}", "warning", duration=7000)

    def _refresh_windows(self, schedule=True):
        scroll_position = self.window_canvas.xview()[0]
        self.windows = self.window_service.list_windows()
        self.card_slots = []
        for widget in self.window_frame.winfo_children():
            widget.destroy()

        if not self.window_service.available:
            tk.Label(
                self.window_frame,
                text="Install wmctrl to show application cards",
                bg=self.COLORS["background"],
                fg=self.COLORS["warning"],
                font=("Inter", 9),
            ).pack(expand=True)
        elif not self.windows:
            tk.Label(
                self.window_frame,
                text="No switchable applications",
                bg=self.COLORS["background"],
                fg=self.COLORS["muted"],
                font=("Inter", 9),
            ).pack(expand=True)
        else:
            for index, window in enumerate(self.windows):
                accent = self.COLORS["primary"] if window.is_vdi else self.COLORS["border"]
                slot = tk.Frame(self.window_frame, width=140, height=44, bg=self.COLORS["background"])
                slot.pack(side="left")
                slot.pack_propagate(False)
                card = tk.Button(
                    slot,
                    text=window.application,
                    command=lambda selected=window: self.activate_window(selected),
                    bg=self.COLORS["surface"],
                    fg=self.COLORS["text"],
                    activebackground=self.COLORS["surface_hover"],
                    activeforeground=self.COLORS["text"],
                    relief="flat",
                    bd=0,
                    highlightthickness=1,
                    highlightbackground=accent,
                    highlightcolor=self.COLORS["primary"],
                    font=("Inter", 9, "bold"),
                    cursor="hand2",
                    takefocus=True,
                )
                card.pack(fill="both", expand=True, padx=3)
                self.card_slots.append((slot, card, window.application))
                card.bind("<Button-4>", lambda _event: self._scroll_windows(-3))
                card.bind("<Button-5>", lambda _event: self._scroll_windows(3))

        self.window_frame.update_idletasks()
        self._update_window_scrollregion()
        self.window_canvas.xview_moveto(scroll_position)
        self.window_count_label.configure(
            text=f"{len(self.windows)} open applications · slide to view all"
        )
        if schedule:
            self.root.after(1800, self._refresh_windows)

    def _update_window_scrollregion(self, _event=None):
        viewport_width = max(1, self.window_canvas.winfo_width())
        columns = max(1, viewport_width // 146)
        slot_width = max(1, viewport_width // columns)
        font = tkfont.Font(font=("Inter", 9, "bold"))
        for slot, card, name in self.card_slots:
            slot.configure(width=slot_width)
            label = name
            while len(label) > 1 and font.measure(label + "…") > slot_width - 24:
                label = label[:-1]
            card.configure(text=label + "…" if label != name else name)
        requested_width = len(self.card_slots) * slot_width if self.card_slots else viewport_width
        self.window_canvas.itemconfigure(
            self.window_canvas_item,
            width=max(requested_width, viewport_width),
            height=44,
        )
        self.window_canvas.configure(scrollregion=(0, 0, max(requested_width, viewport_width), 44))

    def _draw_slider(self, first, last):
        first, last = float(first), float(last)
        width = max(1, self.window_scrollbar.winfo_width())
        self.window_scrollbar.delete("all")
        self.window_scrollbar.create_line(3, 6, width - 3, 6, fill=self.COLORS["surface"], width=4, capstyle="round")
        if last - first < 0.999:
            self.window_scrollbar.create_line(max(3, first * width), 6, min(width - 3, last * width), 6,
                fill="#7d879a", width=4, capstyle="round")

    def _slider_press(self, event):
        first, last = self.window_canvas.xview()
        width = max(1, self.window_scrollbar.winfo_width())
        if first * width <= event.x <= last * width:
            self.slider_anchor = (event.x, first)
        else:
            first = max(0, event.x / width - (last - first) / 2)
            self.window_canvas.xview_moveto(first)
            self.slider_anchor = (event.x, self.window_canvas.xview()[0])

    def _slider_drag(self, event):
        if hasattr(self, "slider_anchor"):
            x, first = self.slider_anchor
            self.window_canvas.xview_moveto(first + (event.x - x) / max(1, self.window_scrollbar.winfo_width()))

    def _resize_window_strip(self, event):
        self.window_canvas.itemconfigure(self.window_canvas_item, height=event.height)
        self._update_window_scrollregion()

    def _scroll_windows(self, direction):
        self.window_canvas.xview_scroll(direction, "units")
        return "break"

    def _activate_visible_index(self, index):
        if 0 <= index < len(self.windows):
            self.activate_window(self.windows[index])

    def activate_window(self, window):
        self.hide()
        self.root.after(80, lambda: self.window_service.activate(window.window_id))

    def paste_clipboard(self):
        try:
            content = self.root.clipboard_get()
        except tk.TclError:
            self._set_status("Host clipboard has no text", "warning")
            return
        if not content:
            self._set_status("Host clipboard has no text", "warning")
            return

        target = self.window_service.preferred_vdi()
        if not target:
            self._set_status("Open Citrix, Remmina, FreeRDP, or VMware Horizon first", "warning")
            return

        self.hide()
        if not self.window_service.activate(target.window_id):
            self._set_status("Could not focus the VDI window", "warning")
            return
        self.root.after(320, lambda: self.clipboard.trigger_paste(content=content))

    def select_screenshot_area(self):
        """Select any region of the full desktop before capturing it."""
        if self.capture_busy:
            return
        self.capture_busy = True
        self.shot_button.configure(state="disabled")
        self.clicker.stop()
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None
        self._set_status("Drag to capture a screen area", "progress", duration=9000)
        self.hide(force=True)
        self.root.withdraw()
        self.root.after(220, self._show_screenshot_selector)

    def _show_screenshot_selector(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window = tk.Toplevel(self.root)
        self.screenshot_window = window
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        try:
            window.attributes("-alpha", 0.28)
        except tk.TclError:
            pass
        window.geometry(f"{screen_width}x{screen_height}+0+0")
        window.configure(bg="#080a0f")

        canvas = tk.Canvas(
            window,
            bg="#080a0f",
            cursor="crosshair",
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill="both", expand=True)
        prompt = canvas.create_text(
            screen_width // 2,
            42,
            text="DRAG TO CAPTURE  ·  ESC TO CANCEL",
            fill="white",
            font=("Inter", 13, "bold"),
        )
        canvas.create_rectangle(
            screen_width // 2 - 190,
            18,
            screen_width // 2 + 190,
            66,
            outline=self.COLORS["primary"],
            width=2,
        )
        canvas.tag_raise(prompt)

        selection = {"start_x": 0, "start_y": 0, "root_x": 0, "root_y": 0, "rect": None}

        def mouse_down(event):
            selection.update(
                start_x=event.x,
                start_y=event.y,
                root_x=event.x_root,
                root_y=event.y_root,
            )
            if selection["rect"]:
                canvas.delete(selection["rect"])
            selection["rect"] = canvas.create_rectangle(
                event.x,
                event.y,
                event.x,
                event.y,
                outline=self.COLORS["primary"],
                width=3,
                dash=(8, 4),
            )

        def mouse_drag(event):
            if selection["rect"]:
                canvas.coords(
                    selection["rect"],
                    selection["start_x"],
                    selection["start_y"],
                    event.x,
                    event.y,
                )

        def mouse_up(event):
            if selection["rect"] is None:
                return
            x1 = min(selection["root_x"], event.x_root)
            y1 = min(selection["root_y"], event.y_root)
            width = abs(event.x_root - selection["root_x"])
            height = abs(event.y_root - selection["root_y"])
            if width < 8 or height < 8:
                self._cancel_screenshot_selection("Selection is too small")
                return
            window.destroy()
            self.screenshot_window = None
            self._set_status(f"Capturing {width}×{height}…", "progress", duration=9000)
            self.root.after(180, lambda: self._capture_screenshot((x1, y1, width, height)))

        canvas.bind("<ButtonPress-1>", mouse_down)
        canvas.bind("<B1-Motion>", mouse_drag)
        canvas.bind("<ButtonRelease-1>", mouse_up)
        window.bind("<Escape>", lambda _event: self._cancel_screenshot_selection())
        window.bind("<Button-3>", lambda _event: self._cancel_screenshot_selection())
        window.lift()
        window.focus_force()
        window.grab_set()

    def _cancel_screenshot_selection(self, message="Screenshot cancelled"):
        if self.screenshot_window:
            self.screenshot_window.destroy()
            self.screenshot_window = None
        self.capture_busy = False
        self.shot_button.configure(state="normal")
        self.root.deiconify()
        self.reveal()
        self._set_status(message, "warning" if "small" in message.lower() else "info")

    def _capture_screenshot(self, region):
        def worker():
            result = self.screenshot_service.capture_to_clipboard(region=region)
            self.ui_queue.put(lambda: self._finish_screenshot(result))

        threading.Thread(target=worker, daemon=True, name="TopDockScreenshot").start()

    def _finish_screenshot(self, result):
        self.capture_busy = False
        self.shot_button.configure(state="normal")
        self.root.deiconify()
        self.reveal()
        self._set_status(result.message, "success" if result.success else "error", duration=7000)

    def select_click_area(self):
        self.hide()
        self.root.after(160, self.clicker.select_area)

    def toggle_clicker(self):
        running = self.clicker.toggle()
        self._update_control_states()
        if running:
            self.hide()

    def toggle_startup(self):
        toggle_startup()
        self._update_control_states()
        self._set_status(
            "Starts with Linux" if is_in_startup() else "Linux startup disabled",
            "success" if is_in_startup() else "info",
        )

    def show_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title("TopDock settings")
        window.configure(bg=self.COLORS["background"])
        window.resizable(False, False)
        window.attributes("-topmost", True)
        window.geometry(f"360x300+{max(0, self.x + self.width - 360)}+{self.HEIGHT + 8}")
        tk.Label(window, text="TopDock settings", font=("Inter", 14, "bold"),
            bg=self.COLORS["background"], fg=self.COLORS["text"]).pack(anchor="w", padx=20, pady=(20, 12))
        tk.Label(window, text="Ctrl + Alt + Space  ·  Reveal dock\nDrag the slider  ·  Browse applications\nSHOT  ·  Select any desktop area\nEscape / right-click  ·  Cancel capture",
            justify="left", font=("Inter", 10), bg=self.COLORS["background"], fg=self.COLORS["muted"]).pack(anchor="w", padx=20)
        tk.Label(window, text="Made with love by Aditya Rathee", font=("Inter", 10, "bold"),
            bg=self.COLORS["background"], fg="#d8b4fe").pack(pady=20)
        tk.Button(window, text="Exit TopDock", command=self.exit, bg=self.COLORS["surface"],
            fg=self.COLORS["danger"], relief="flat", padx=16, pady=8).pack()
        def close_settings():
            window.destroy()
            self.settings_window = None
        window.protocol("WM_DELETE_WINDOW", close_settings)
        window.bind("<Escape>", lambda _e: close_settings())

    def _drain_ui_queue(self):
        while True:
            try:
                callback = self.ui_queue.get_nowait()
            except Empty:
                break
            callback()
        self.root.after(50, self._drain_ui_queue)

    def toggle_pin(self):
        self.pinned = not self.pinned
        self._update_control_states()
        self._set_status("Dock pinned open" if self.pinned else "Dock auto-hide enabled", "info")

    def _update_control_states(self):
        if hasattr(self, "clicker"):
            running = self.clicker.clicking
            self.auto_button.configure(
                text="◎\nAUTO ON" if running else "◎\nAUTO OFF",
                fg=self.COLORS["success"] if running else self.COLORS["text"],
            )
            self.area_button.configure(
                fg=self.COLORS["primary"] if self.clicker.selection_coords else self.COLORS["text"]
            )
        self.startup_button.configure(
            text="START ✓" if is_in_startup() else "START",
            fg=self.COLORS["success"] if is_in_startup() else self.COLORS["text"],
        )
        self.pin_button.configure(
            text="PIN ✓" if self.pinned else "PIN",
            fg=self.COLORS["primary"] if self.pinned else self.COLORS["text"],
        )

    def _module_status(self, message, message_type="info"):
        self.ui_queue.put(lambda: self._handle_module_status(message, message_type))

    def _handle_module_status(self, message, message_type):
        self._update_control_states()
        self._set_status(message, message_type)

    def _set_status(self, message, message_type="info", duration=4200):
        colors = {
            "success": self.COLORS["success"],
            "warning": self.COLORS["warning"],
            "error": self.COLORS["danger"],
            "info": self.COLORS["muted"],
            "progress": self.COLORS["primary"],
        }
        self.status_label.configure(text=str(message)[:34], fg=colors.get(message_type, self.COLORS["muted"]))
        self.status_until = time.monotonic() + duration / 1000

    def _update_clock(self):
        if time.monotonic() >= self.status_until:
            now = datetime.now().strftime("%a, %I:%M %p").replace(" 0", " ")
            self.status_label.configure(text=now, fg=self.COLORS["muted"])
        self.root.after(1000, self._update_clock)

    def _track_pointer(self):
        if self.capture_busy or self.settings_window:
            self.root.after(70, self._track_pointer)
            return
        try:
            pointer_x = self.root.winfo_pointerx()
            pointer_y = self.root.winfo_pointery()
        except tk.TclError:
            return

        if pointer_y <= 2:
            self.reveal()

        inside = self.x <= pointer_x <= self.x + self.width and 0 <= pointer_y <= self.HEIGHT + 4
        if inside:
            self.last_inside = time.monotonic()
        elif self.is_shown and not self.pinned and time.monotonic() - self.last_inside > 0.8:
            self.hide()

        self.root.after(70, self._track_pointer)

    def reveal(self):
        if self.capture_busy:
            return
        self.is_shown = True
        self.last_inside = time.monotonic()
        self._animate_to(self.shown_y)

    def hide(self, force=False):
        if self.pinned and not force:
            return
        self.is_shown = False
        self._animate_to(self.hidden_y)

    def _animate_to(self, target_y):
        if self.animation_id:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None

        current_y = self.root.winfo_y()
        distance = target_y - current_y
        if abs(distance) <= 2:
            self._set_geometry(target_y)
            return
        step = max(-16, min(16, distance))
        next_y = current_y + step
        self._set_geometry(next_y)
        self.animation_id = self.root.after(12, lambda: self._animate_to(target_y))

    def _set_geometry(self, y):
        y_position = f"+{y}"
        self.root.geometry(f"{self.width}x{self.HEIGHT}+{self.x}{y_position}")

    def exit(self):
        try:
            if self.screenshot_window:
                self.screenshot_window.destroy()
            self.clipboard.cleanup()
            self.clicker.cleanup()
            if self.hotkey_listener:
                self.hotkey_listener.stop()
        finally:
            self.root.destroy()


def main():
    if not IS_LINUX:
        print("Linux TopDock must be run from a Linux desktop session.")
        return 1

    required_modules = {
        "pyperclip": "pyperclip",
        "pyautogui": "pyautogui",
        "pynput": "pynput",
    }
    issues = check_required_modules(required_modules=required_modules)

    if "--check" in sys.argv:
        print("TopDock VDI Linux diagnostics")
        print(f"  Platform: {sys.platform}")
        print(f"  Dependencies: {'OK' if not issues else 'FAILED'}")
        print(f"  wmctrl: {'OK' if X11WindowService().available else 'MISSING'}")
        warnings = get_linux_runtime_warnings()
        for warning in warnings:
            print(f"  Warning: {warning}")
        if issues:
            print_startup_report(issues)
        return 1 if issues or not X11WindowService().available else 0

    if issues:
        print_startup_report(issues)
        return 1

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"[ERROR] Could not connect to the Linux desktop: {exc}")
        return 1

    LinuxTopDock(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
