#!/usr/bin/env python3
"""Premium auto-hiding TopDock for Linux/X11 VDI workflows."""

from datetime import datetime
from io import BytesIO
from pathlib import Path
import json
import os
import shutil
import portable_runtime  # Make bundled X11 helpers available before other imports.
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import time
import tkinter as tk
from tkinter import font as tkfont, ttk
from queue import SimpleQueue, Empty

from PIL import Image, ImageDraw

from linux_screenshot_service import LinuxScreenshotService
from linux_window_service import X11WindowService
from platform_utils import IS_LINUX, get_config_dir, get_linux_runtime_warnings, is_in_startup, toggle_startup
from startup_diagnostics import check_required_modules, print_startup_report


class LinuxTopDock:
    TITLE = "TopDock Linux"
    VERSION = "1.4.0"
    HEIGHT = 76
    EDGE_HEIGHT = 4
    EDGE_REVEAL_DELAY = 0.75
    EDGE_REVEAL_OPTIONS = {
        "delayed": f"After {EDGE_REVEAL_DELAY:g} seconds",
        "immediate": "Immediately",
        "shortcut": "Shortcut only",
    }
    QUICK_ACTION_IDS = ("paste", "shot", "auto", "search", "pin", "settings")

    COLORS = {
        "background": "#15181f",
        "surface": "#20232b",
        "surface_hover": "#292d37",
        "border": "#323744",
        "text": "#f7f8fa",
        "muted": "#a6adbb",
        "primary": "#e20acf",
        "primary_dark": "#a60098",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    }

    def __init__(self, root):
        self.root = root
        self.window_service = X11WindowService(self.TITLE)
        self.width = max(1, min(1240, root.winfo_screenwidth() - 48))
        self.ui_settings_path = get_config_dir() / "topdock-ui.json"
        self.ui_settings = self._load_ui_settings()
        self.quick_order = self.ui_settings["quick_order"]
        self.quick_hidden = set(self.ui_settings["quick_hidden"])
        self.show_window_search = self.ui_settings["show_window_search"]
        self.compact_mode = self.ui_settings["compact_mode"]
        self.x = max(0, min(root.winfo_screenwidth() - self.width,
            self.ui_settings.get("x", (root.winfo_screenwidth() - self.width) // 2)))
        self.shown_y = max(0, min(root.winfo_screenheight() - self.HEIGHT,
            self.ui_settings.get("y", 0)))
        self.hidden_y = -(self.HEIGHT - self.EDGE_HEIGHT)
        self.is_shown = True
        self.pinned = self.ui_settings["pinned"]
        self.edge_reveal_mode = self.ui_settings["edge_reveal_mode"]
        self.edge_entered_at = None
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
        self.window_icons = {}
        self.collapsed = False
        self.drag_origin = None
        self.search_query = ""
        self.search_open = False
        self.clipboard_window = None
        self.quick_drag = None
        self.click_area_pending = False

        self._configure_window()
        self._configure_dock_styles()
        self._build_ui()
        self._shape_size = None
        self.root.bind("<Configure>", self._shape_dock)
        self.root.bind("<Control-f>", self._open_search)
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
            persist_area=False,
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
        self.outer = outer

        content = tk.Frame(outer, bg=self.COLORS["background"])
        content.pack(fill="both", expand=True, padx=12, pady=8)
        content.grid_columnconfigure(2, weight=1)
        content.grid_rowconfigure(0, weight=1)

        brand = tk.Frame(content, bg=self.COLORS["background"], width=164)
        brand.grid(row=0, column=0, sticky="ns")
        brand.pack_propagate(False)

        self.brand_icon = self._brand_icon()
        logo = tk.Label(brand, image=self.brand_icon, bg=self.COLORS["background"], bd=0)
        logo.pack(side="left", padx=(0, 8))
        for handle in (brand, logo):
            handle.bind("<ButtonPress-1>", self._drag_start)
            handle.bind("<B1-Motion>", self._drag_move)
            handle.bind("<ButtonRelease-1>", self._drag_end)

        brand_text = tk.Frame(brand, bg=self.COLORS["background"])
        brand_text.pack(side="left", fill="y")
        tk.Label(
            brand_text,
            text="T O P D O C K",
            bg=self.COLORS["background"],
            fg=self.COLORS["text"],
            font=("Inter", 10, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))
        self.status_label = tk.Label(
            brand_text,
            text="Ready",
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

        self.paste_button = self._tool_button(tools, "PASTE", self.paste_clipboard, width=58, style="Paste", icon="paste")
        self.shot_button = self._tool_button(tools, "SHOT", self.select_screenshot_area, width=50, style="Shot", icon="shot")
        self.auto_button = self._tool_button(tools, "AUTO", self._show_auto_menu, width=62, icon="auto")
        self.search_button = self._tool_button(tools, "", self._open_search, icon="search")
        self.pin_button = self._tool_button(tools, "", self.toggle_pin, icon="pin")
        self.settings_button = self._tool_button(tools, "", self.show_settings, icon="settings")
        self.quick_buttons = dict(zip(self.QUICK_ACTION_IDS, (
            self.paste_button, self.shot_button, self.auto_button, self.search_button,
            self.pin_button, self.settings_button,
        )))
        for key, button in self.quick_buttons.items():
            button.bind("<ButtonPress-1>", lambda event, action=key: self._quick_drag_start(action, event))
            button.bind("<ButtonRelease-1>", lambda event, action=key: self._quick_drag_end(action, event))
        self._apply_quick_action_layout()
        self.auto_menu = tk.Menu(self.root, tearoff=False, bg="#1e222c", fg=self.COLORS["text"],
                                 activebackground=self.COLORS["surface_hover"], activeforeground=self.COLORS["text"])
        self.search_panel = tk.Frame(outer, bg=self.COLORS["background"], padx=16, pady=12)
        close_search = self._tool_button(self.search_panel, "×", self._close_search)
        close_search.master.pack(side="right", padx=(8, 0))
        tk.Label(self.search_panel, text="Search windows", bg=self.COLORS["background"],
                 fg=self.COLORS["text"]).pack(side="left", padx=(0, 12))
        self.search_input = tk.StringVar()
        self.search_entry = tk.Entry(self.search_panel, textvariable=self.search_input,
                                     bg=self.COLORS["surface"], fg=self.COLORS["text"],
                                     insertbackground=self.COLORS["text"], relief="flat")
        self.search_entry.pack(side="left", fill="both", expand=True, ipady=6)
        self.search_input.trace_add("write", lambda *_: self._set_search_query(self.search_input.get()))
        self.search_entry.bind("<Escape>", self._close_search)
        self.search_entry.bind("<Return>", lambda _event: self._activate_visible_index(0))
        self.circle = tk.Button(self.root, text="⌃", command=self.expand_dock,
            bg=self.COLORS["primary"], fg="white", activebackground=self.COLORS["primary_dark"],
            activeforeground="white", relief="flat", bd=0, font=("Inter", 24, "bold"), cursor="hand2")
        self.circle.bind("<ButtonPress-1>", self._drag_start, add="+")
        self.circle.bind("<B1-Motion>", self._drag_move, add="+")
        self.circle.bind("<ButtonRelease-1>", self._drag_end, add="+")
        self._update_control_states()

    def _load_ui_settings(self):
        defaults = {
            "quick_order": list(self.QUICK_ACTION_IDS),
            "quick_hidden": [],
            "pinned": False,
            "show_window_search": False,
            "compact_mode": False,
            "edge_reveal_mode": "delayed",
        }
        try:
            value = json.loads(self.ui_settings_path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                return defaults
        except (OSError, ValueError):
            return defaults
        order = value.get("quick_order", [])
        hidden = value.get("quick_hidden", [])
        if not isinstance(order, list):
            order = []
        if not isinstance(hidden, list):
            hidden = []
        defaults["quick_order"] = [key for key in order if key in self.QUICK_ACTION_IDS]
        defaults["quick_order"] = list(dict.fromkeys(defaults["quick_order"] + list(self.QUICK_ACTION_IDS)))
        defaults["quick_hidden"] = [key for key in hidden if key in {"paste", "shot", "auto"}]
        defaults["pinned"] = value.get("pinned") is True
        defaults["show_window_search"] = value.get("show_window_search") is True
        defaults["compact_mode"] = value.get("compact_mode") is True
        mode = value.get("edge_reveal_mode")
        if isinstance(mode, str) and mode in self.EDGE_REVEAL_OPTIONS:
            defaults["edge_reveal_mode"] = mode
        for key in ("x", "y"):
            if isinstance(value.get(key), int) and not isinstance(value[key], bool):
                defaults[key] = value[key]
        return defaults

    def _save_ui_settings(self):
        payload = {
            "quick_order": self.quick_order, "quick_hidden": sorted(self.quick_hidden),
            "pinned": self.pinned, "edge_reveal_mode": self.edge_reveal_mode,
            "show_window_search": self.show_window_search, "compact_mode": self.compact_mode,
            "x": self.x, "y": self.shown_y,
        }
        try:
            self.ui_settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.ui_settings_path.with_name(".topdock-ui.json.tmp")
            temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, self.ui_settings_path)
        except OSError:
            self._set_status("Could not save dock preferences", "warning")

    def _apply_quick_action_layout(self):
        shells = {key: button.master for key, button in self.quick_buttons.items()}
        for shell in shells.values():
            shell.pack_forget()
        for key in self.quick_order:
            if key not in self.quick_hidden and (key != "search" or self.show_window_search):
                shells[key].pack(side="left", padx=2)

    def _quick_drag_start(self, action, event):
        self.quick_drag = (action, event.x_root, event.y_root)

    def _quick_drag_end(self, action, event):
        if not self.quick_drag or self.quick_drag[0] != action:
            return
        _, start_x, start_y = self.quick_drag
        self.quick_drag = None
        if abs(event.x_root - start_x) + abs(event.y_root - start_y) < 7:
            return
        target = self.root.winfo_containing(event.x_root, event.y_root)
        shells = {key: button.master for key, button in self.quick_buttons.items()}
        while target is not None and target not in shells.values():
            target = target.master
        if target is None:
            return
        target_id = next(key for key, shell in shells.items() if shell == target)
        if target_id == action:
            return
        self.quick_order.remove(action)
        index = self.quick_order.index(target_id)
        if event.x_root > target.winfo_rootx() + target.winfo_width() / 2:
            index += 1
        self.quick_order.insert(index, action)
        self._apply_quick_action_layout()
        self._save_ui_settings()

    def _toggle_quick_action(self, action, variable):
        if variable.get():
            self.quick_hidden.discard(action)
        else:
            self.quick_hidden.add(action)
        self._apply_quick_action_layout()
        self._save_ui_settings()

    def _configure_dock_styles(self):
        style = ttk.Style(self.root)
        self.dock_style_images = []
        palettes = {
            "Action": ("#1f2229", "#272a31"),
            "Paste": ("#201e33", "#2b254b"),
            "Shot": ("#1e1d30", "#252142"),
            "PinOn": ("#381434", "#5b1c53"),
            "AutoOn": ("#153023", "#20513a"),
            "Card": ("#1c1f26", "#272a31"),
            "CardActive": ("#272a31", "#41444a"),
        }
        for name, (fill, border) in palettes.items():
            images = []
            for state_fill, state_border in ((fill, border), ("#242932", "#44474d"),
                                              (fill, self.COLORS["primary"]), ("#191b21", border)):
                shape = Image.new("RGB", (36, 36), self.COLORS["background"])
                draw = ImageDraw.Draw(shape)
                draw.rounded_rectangle((0, 0, 35, 35), radius=11, fill=state_fill, outline=state_border)
                images.append(self._tk_image(shape))
            normal, hover, focus, pressed = images
            self.dock_style_images.extend(images)
            element = f"TopDock.{name}.surface"
            style.element_create(element, "image", normal, ("pressed", pressed),
                                 ("focus", focus), ("active", hover), border=12, padding=2, sticky="nsew")
            style_name = f"TopDock.{name}.TButton"
            style.layout(style_name, [(element, {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})
            ]})])
            is_card = name.startswith("Card")
            style.configure(style_name, foreground=self.COLORS["text"],
                            anchor="w" if is_card else "center",
                            padding=(8, 0) if is_card else 0,
                            font=("Inter", 9 if is_card else 8, "bold"))

    def _tool_button(self, parent, text, command, width=40, style="Action", icon=None):
        shell = tk.Frame(parent, width=width, height=40, bg=self.COLORS["background"])
        shell.pack_propagate(False)
        button = ttk.Button(shell, text=text, command=command, style=f"TopDock.{style}.TButton",
                            cursor="hand2", takefocus=True)
        if icon:
            button.icon = self._tool_icon(icon)
            button.configure(image=button.icon, compound="top")
        button.pack(fill="both", expand=True)
        return button

    @staticmethod
    def _tk_image(image):
        with BytesIO() as buffer:
            image.save(buffer, format="PNG")
            return tk.PhotoImage(data=buffer.getvalue(), format="png")

    def _brand_icon(self):
        size = 68
        image = Image.new("RGBA", (size, size))
        draw = ImageDraw.Draw(image)
        for y in range(size):
            for x in range(size):
                progress = (x + y) / (2 * (size - 1))
                image.putpixel((x, y), (round(200 + 30 * progress), 0, round(223 - 105 * progress), 255))
        mask = Image.new("L", image.size)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=19, fill=255)
        image.putalpha(mask)
        draw.line((23, 39, 34, 28, 45, 39), fill="white", width=4, joint="curve")
        return self._tk_image(image.resize((34, 34), Image.Resampling.LANCZOS))

    def _tool_icon(self, name):
        image = Image.new("RGBA", (32, 32))
        draw = ImageDraw.Draw(image)
        ink = "#f8fafc"
        if name == "paste":
            draw.rounded_rectangle((7, 6, 25, 28), radius=3, outline=ink, width=2)
            draw.rounded_rectangle((12, 3, 20, 9), radius=2, fill=ink)
            draw.line((11, 16, 21, 16), fill=ink, width=2)
            draw.line((11, 21, 20, 21), fill=ink, width=2)
        elif name == "shot":
            for x, y, dx, dy in ((4, 4, 1, 1), (27, 4, -1, 1), (4, 27, 1, -1), (27, 27, -1, -1)):
                draw.line((x + 7 * dx, y, x, y, x, y + 7 * dy), fill=ink, width=2)
            draw.ellipse((13, 13, 18, 18), fill=ink)
        elif name == "auto":
            draw.ellipse((4, 4, 27, 27), outline=ink, width=2)
            draw.ellipse((10, 10, 21, 21), outline=ink, width=2)
        elif name == "search":
            draw.ellipse((5, 4, 22, 21), outline=ink, width=2)
            draw.line((19, 19, 27, 27), fill=ink, width=3)
        elif name == "pin":
            draw.line((11, 6, 22, 6, 21, 15, 25, 20, 7, 20, 11, 15, 11, 6),
                      fill=ink, width=2, joint="curve")
            draw.line((16, 20, 16, 28), fill=ink, width=2)
        else:
            for x, y, dx, dy in ((16, 5, 0, -3), (16, 26, 0, 3), (5, 16, -3, 0),
                                 (26, 16, 3, 0), (8, 8, -2, -2), (23, 8, 2, -2),
                                 (8, 23, -2, 2), (23, 23, 2, 2)):
                draw.line((x, y, x + dx, y + dy), fill=ink, width=3)
            draw.ellipse((5, 5, 26, 26), outline=ink, width=2)
            draw.ellipse((12, 12, 19, 19), outline=ink, width=2)
        return self._tk_image(image.resize((16, 16), Image.Resampling.LANCZOS))

    def _drag_start(self, event):
        self.drag_origin = (event.x_root, event.y_root, self.x, self.shown_y)
        self.drag_moved = False

    def _drag_move(self, event):
        if not self.drag_origin:
            return
        px, py, start_x, start_y = self.drag_origin
        if abs(event.x_root - px) + abs(event.y_root - py) < 4 and not self.drag_moved:
            return
        self.drag_moved = True
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        visible_width = 60 if self.collapsed else self.width
        visible_height = 60 if self.collapsed else self.HEIGHT
        self.x = max(0, min(screen_width - visible_width, start_x + event.x_root - px))
        self.shown_y = max(0, min(screen_height - visible_height, start_y + event.y_root - py))
        self.hidden_y = -(self.HEIGHT - self.EDGE_HEIGHT)
        self.is_shown = True
        self._set_geometry(self.shown_y)

    def _drag_end(self, _event):
        if self.collapsed and self.drag_moved:
            self.circle.after_idle(lambda: self.circle.configure(command=self.expand_dock))
        if self.drag_moved:
            self._save_ui_settings()
        self.drag_origin = None

    def collapse_dock(self):
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None
        self.collapsed = True
        self.edge_entered_at = None
        self.outer.pack_forget()
        self.circle.pack(fill="both", expand=True)
        self.root.geometry(f"60x60+{self.x}+{self.shown_y}")
        self.root.update_idletasks()
        self._shape_dock()
        self.is_shown = True

    def expand_dock(self):
        if not self.collapsed or getattr(self, "drag_moved", False):
            self.drag_moved = False
            return
        self.collapsed = False
        self.circle.pack_forget()
        self.outer.pack(fill="both", expand=True)
        self.x = max(0, min(self.x, self.root.winfo_screenwidth() - self.width))
        self._set_geometry(self.shown_y)
        self.reveal()

    def _shape_dock(self, event=None):
        """Shape the X11 dock window to match its rounded frame."""
        if event is not None and event.widget is not self.root:
            return
        width, height = self.root.winfo_width(), self.root.winfo_height()
        if width < 2 or height < 2 or self._shape_size == (width, height, self.collapsed):
            return
        self._shape_size = (width, height, self.collapsed)
        image = Image.new("1", (width, height))
        radius = min(width, height) // 2 if self.collapsed else 20
        ImageDraw.Draw(image).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=1)
        # X11 bitmaps store the leftmost pixel in the least significant bit.
        reverse_bits = bytes(int(f"{value:08b}"[::-1], 2) for value in range(256))
        data = image.tobytes().translate(reverse_bits)
        try:
            import ctypes
            import ctypes.util

            x11 = ctypes.CDLL(ctypes.util.find_library("X11"))
            xext = ctypes.CDLL(ctypes.util.find_library("Xext"))
            x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            x11.XOpenDisplay.restype = ctypes.c_void_p
            x11.XCreateBitmapFromData.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint]
            x11.XCreateBitmapFromData.restype = ctypes.c_ulong
            x11.XFreePixmap.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
            xext.XShapeCombineMask.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong, ctypes.c_int]
            display = x11.XOpenDisplay(None)
            if not display:
                return
            try:
                window_id = self.root.winfo_id()
                mask = x11.XCreateBitmapFromData(display, window_id, data, width, height)
                if mask:
                    xext.XShapeCombineMask(display, window_id, 0, 0, 0, mask, 0)
                    x11.XFreePixmap(display, mask)
            finally:
                x11.XCloseDisplay(display)
        except (OSError, AttributeError):
            pass

    def show_clipboard_preview(self):
        if self.clipboard_window and self.clipboard_window.winfo_exists():
            self.clipboard_window.lift()
            return
        image = None
        try:
            selection = subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=2)
            if selection.returncode == 0 and selection.stdout:
                image = Image.open(BytesIO(selection.stdout)).copy()
        except (OSError, subprocess.TimeoutExpired, ValueError):
            pass
        try:
            content = self.root.clipboard_get() if image is None else None
        except tk.TclError:
            content = "Clipboard has no text or PNG image to preview."
        window = tk.Toplevel(self.root)
        self.clipboard_window = window
        window.title("Clipboard preview")
        window.configure(bg=self.COLORS["background"])
        window.geometry(f"500x350+{max(0, self.x + self.width - 500)}+{self.shown_y + self.HEIGHT + 8}")
        window.attributes("-topmost", True)
        header = tk.Frame(window, bg=self.COLORS["background"])
        header.pack(fill="x", padx=14, pady=10)
        tk.Label(header, text="Clipboard preview", bg=self.COLORS["background"],
            fg=self.COLORS["text"], font=("Inter", 12, "bold")).pack(side="left")
        size = {"value": 12}
        zoom = tk.Label(header, text="100%", bg=self.COLORS["background"], fg=self.COLORS["muted"])
        zoom.pack(side="right", padx=8)
        text = None
        canvas = None
        if image is None:
            text = tk.Text(window, bg=self.COLORS["surface"], fg=self.COLORS["text"],
                insertbackground=self.COLORS["text"], font=("DejaVu Sans Mono", 12), wrap="none")
            text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
            text.insert("1.0", content)
            text.configure(state="disabled")
        else:
            canvas = tk.Canvas(window, bg=self.COLORS["surface"], highlightthickness=0)
            canvas.pack(fill="both", expand=True, padx=14, pady=(0, 14))
            scale = {"value": min(1, 450 / image.width, 260 / image.height)}
            def redraw():
                width = max(1, round(image.width * scale["value"]))
                height = max(1, round(image.height * scale["value"]))
                canvas.preview = self._tk_image(image.resize((width, height), Image.Resampling.LANCZOS))
                canvas.delete("all")
                canvas.create_image(0, 0, image=canvas.preview, anchor="nw")
                canvas.configure(scrollregion=(0, 0, width, height))
                zoom.configure(text=f"{round(scale['value'] * 100)}%")
            redraw()
            canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
            canvas.bind("<Shift-MouseWheel>", lambda e: canvas.xview_scroll(-1 if e.delta > 0 else 1, "units"))
        def adjust(delta):
            if canvas is not None:
                scale["value"] = max(0.1, min(4, scale["value"] * (1.25 if delta > 0 else 0.8)))
                redraw()
            else:
                size["value"] = max(10, min(32, size["value"] + delta))
                text.configure(font=("DejaVu Sans Mono", size["value"]))
                zoom.configure(text=f"{round(size['value'] / 12 * 100)}%")
        tk.Button(header, text="+", width=3, command=lambda: adjust(2)).pack(side="right")
        tk.Button(header, text="−", width=3, command=lambda: adjust(-2)).pack(side="right")
        window.protocol("WM_DELETE_WINDOW", lambda: (window.destroy(), setattr(self, "clipboard_window", None)))

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

            def toggle_on_main_thread():
                self.ui_queue.put(self._toggle_dock)

            # Some X11 pynput builds normalize Space to keysym 32.
            self.hotkey_listener = pynput_keyboard.GlobalHotKeys({
                "<ctrl>+<alt>+<space>": toggle_on_main_thread,
                "<ctrl>+<alt>+<32>": toggle_on_main_thread,
            })
            self.hotkey_listener.start()
        except Exception as exc:
            self.hotkey_listener = None
            self._set_status(f"Reveal hotkey unavailable: {exc}", "warning", duration=7000)

    def _refresh_windows(self, schedule=True):
        scroll_position = self.window_canvas.xview()[0]
        self.windows = self.window_service.list_windows()
        if self.search_query:
            query = self.search_query.casefold()
            self.windows = [item for item in self.windows
                            if query in item.application.casefold() or query in item.title.casefold()]
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
            active_id = self.window_service.active_window_id()
            visible_ids = {window.window_id for window in self.windows}
            self.window_icons = {key: icon for key, icon in self.window_icons.items() if key in visible_ids}
            for key, icon in self.window_service.window_icons(visible_ids - self.window_icons.keys()).items():
                self.window_icons[key] = self._card_icon(icon)
            for index, window in enumerate(self.windows):
                active = active_id and int(window.window_id, 16) == int(active_id, 16)
                slot = tk.Frame(self.window_frame, width=140, height=44, bg=self.COLORS["background"])
                slot.pack(side="left")
                slot.pack_propagate(False)
                card = ttk.Button(
                    slot,
                    text=window.application,
                    image=self.window_icons[window.window_id],
                    compound="left",
                    command=lambda selected=window: self.activate_window(selected),
                    style="TopDock.CardActive.TButton" if active else "TopDock.Card.TButton",
                    cursor="hand2",
                    takefocus=True,
                )
                if index < 9:
                    hint = tk.Label(slot, text=f"ALT {index + 1}", bg="#242932", fg="#cbd5e1",
                                    font=("Inter", 6), padx=2, pady=0)
                    card.bind("<Enter>", lambda _event, badge=hint: badge.place(relx=1, x=-9, y=2, anchor="ne"))
                    card.bind("<Leave>", lambda _event, badge=hint: badge.place_forget())
                    card.bind("<FocusIn>", lambda _event, badge=hint: badge.place(relx=1, x=-9, y=2, anchor="ne"))
                    card.bind("<FocusOut>", lambda _event, badge=hint: badge.place_forget())
                card.pack(fill="both", expand=True, padx=3)
                if active:
                    indicator = tk.Frame(card, width=24, height=2, bg=self.COLORS["primary"])
                    indicator.place(relx=0.5, rely=1, y=-2, anchor="s")
                    indicator.bind("<Button-1>", lambda _event, button=card: button.invoke())
                    indicator.bind("<Button-2>", lambda _event, selected=window: self._close_window(selected))
                self.card_slots.append((slot, card, window.application))
                card.bind("<Button-2>", lambda _event, selected=window: self._close_window(selected))
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

    def _card_icon(self, raw_icon):
        tile = Image.new("RGBA", (34, 27))
        draw = ImageDraw.Draw(tile)
        draw.rounded_rectangle((0, 0, 26, 26), radius=8, fill="#2b2e35", outline="#373941")
        if raw_icon:
            width, height, pixels = raw_icon
            icon = Image.frombytes("RGBA", (width, height), pixels)
            icon.thumbnail((18, 18), Image.Resampling.LANCZOS)
            tile.alpha_composite(icon, ((27 - icon.width) // 2, (27 - icon.height) // 2))
        else:
            draw.rounded_rectangle((6, 7, 20, 19), radius=2, outline="#b8c2d1")
            draw.line((7, 10, 19, 10), fill="#b8c2d1")
        return self._tk_image(tile)

    def _update_window_scrollregion(self, _event=None):
        viewport_width = max(1, self.window_canvas.winfo_width())
        preferred_width = 130 if self.compact_mode else 146
        columns = max(1, viewport_width // preferred_width)
        slot_width = max(1, viewport_width // columns)
        font = tkfont.Font(font=("Inter", 9, "bold"))
        for slot, card, name in self.card_slots:
            slot.configure(width=slot_width)
            label = name
            while len(label) > 1 and font.measure(label + "…") > slot_width - 54:
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
        self._close_search()
        self.hide()
        self.root.after(80, lambda: self.window_service.activate(window.window_id))

    def _close_window(self, window):
        if self.window_service.close(window.window_id):
            self.root.after(150, lambda: self._refresh_windows(schedule=False))
        return "break"

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

    @staticmethod
    def _set_screenshot_cursor(canvas):
        size = 42
        center = size // 2

        def xbm(stroke):
            pixels = bytearray(((size + 7) // 8) * size)
            for y in range(size):
                for x in range(size):
                    dx, dy = abs(x - center), abs(y - center)
                    if (dx <= stroke and 4 <= dy <= 17) or (dy <= stroke and 4 <= dx <= 17):
                        pixels[y * ((size + 7) // 8) + x // 8] |= 1 << (x % 8)
            values = ", ".join(f"0x{value:02x}" for value in pixels)
            return (f"#define cross_width {size}\n#define cross_height {size}\n"
                    f"#define cross_x_hot {center}\n#define cross_y_hot {center}\n"
                    f"static unsigned char cross_bits[] = {{ {values} }};\n")

        try:
            with TemporaryDirectory(prefix="topdock-cursor-") as directory:
                source, mask = Path(directory) / "cross.xbm", Path(directory) / "mask.xbm"
                source.write_text(xbm(1), encoding="ascii")
                mask.write_text(xbm(3), encoding="ascii")
                canvas.configure(cursor=(f"@{source}", str(mask), "#ffea00", "#101010"))
        except (OSError, tk.TclError):
            canvas.configure(cursor="crosshair #ffea00")

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
            highlightthickness=0,
            bd=0,
        )
        self._set_screenshot_cursor(canvas)
        canvas.pack(fill="both", expand=True)
        prompt = canvas.create_text(
            screen_width // 2,
            42,
            text="Drag to capture  ·  Esc or right-click to cancel",
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
                width=2,
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

    def _show_auto_menu(self):
        area = self.clicker.selection_coords
        if area is None:
            self.select_click_area()
            return
        x1, y1, x2, y2 = area
        self.auto_menu.delete(0, "end")
        self.auto_menu.add_command(label="Stop auto clicker" if self.clicker.clicking else "Start auto clicker",
                                   command=self.toggle_clicker)
        self.auto_menu.add_command(label="Select click area…", command=self.select_click_area)
        self.auto_menu.add_separator()
        self.auto_menu.add_command(label=f"{x2 - x1} × {y2 - y1}px at {x1}, {y1}", state="disabled")
        try:
            self.auto_menu.tk_popup(self.auto_button.winfo_rootx(),
                                    self.auto_button.winfo_rooty() + self.auto_button.winfo_height())
        finally:
            self.auto_menu.grab_release()

    def select_click_area(self):
        if self.click_area_pending or self.clicker.selection_window:
            return
        self.clicker.stop()
        self._update_control_states()
        self.hide(force=True)
        self.click_area_pending = True

        def begin_selection():
            self.click_area_pending = False
            self.clicker.select_area()
            selector = self.clicker.selection_window
            if selector is not None and self.pinned:
                selector.bind("<Destroy>", lambda event: self.root.after_idle(self.reveal)
                              if event.widget is selector else None, add="+")

        self.root.after(160, begin_selection)

    def toggle_clicker(self):
        if not self.clicker.selection_coords:
            self.select_click_area()
            return
        running = self.clicker.toggle()
        self._update_control_states()
        if running:
            self.hide()
            target = self.window_service.preferred_vdi()
            if target:
                self.root.after(80, lambda: self.window_service.activate(target.window_id))

    def _open_zoom_clipboard(self):
        data_dir = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        frozen = getattr(sys, "frozen", False)
        base = Path(sys.executable if frozen else __file__).resolve().parent
        companion = Path("zoom-clipboard", "linux", "zoom_clipboard.py")
        paths = (base / companion, data_dir / "zoom-clipboard" / "zoom_clipboard.py", base.parent / companion)
        script = next((path for path in paths if path.is_file()), None)
        if script is None:
            self._set_zoom_status("Install Zoom Clipboard for Linux to open it here.")
            return
        python = shutil.which("python3") if frozen else sys.executable
        if not python:
            self._set_zoom_status("Zoom Clipboard requires Python 3.")
            return
        launch_env = None
        if frozen:
            launch_env = os.environ.copy()
            original_libraries = launch_env.pop("LD_LIBRARY_PATH_ORIG", None)
            if original_libraries is None:
                launch_env.pop("LD_LIBRARY_PATH", None)
            else:
                launch_env["LD_LIBRARY_PATH"] = original_libraries
        try:
            subprocess.Popen([python, str(script)], start_new_session=True, env=launch_env)
        except OSError as exc:
            self._set_zoom_status(f"Could not open Zoom Clipboard: {exc}")
            return
        self._set_zoom_status("Opening Zoom Clipboard…")

    def _set_zoom_status(self, text):
        self.zoom_status.configure(text=text)
        self.zoom_status.pack(before=self.zoom_divider, anchor="w", padx=20)

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
        self._close_search()
        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title("TopDock settings")
        panel = "#1e222c"
        window.configure(bg=panel)
        window.resizable(False, False)
        window.attributes("-topmost", True)

        def close_settings(_event=None):
            window.destroy()
            self.settings_window = None
            self.last_inside = time.monotonic()

        header = tk.Frame(window, bg=panel)
        header.pack(fill="x", padx=18, pady=(14, 8))
        tk.Label(header, text="TopDock settings", font=("Inter", 12, "bold"),
                 bg=panel, fg=self.COLORS["text"]).pack(side="left")
        tk.Button(header, text="×", command=close_settings, bg=self.COLORS["surface"],
                  fg=self.COLORS["text"], relief="flat", cursor="hand2",
                  highlightbackground=panel, highlightcolor=self.COLORS["primary"]).pack(side="right")

        def checkbox(text, value, apply):
            state = tk.BooleanVar(window, value=value)
            tk.Checkbutton(window, text=text, variable=state, command=lambda: apply(state.get()),
                           bg=panel, fg=self.COLORS["text"], activebackground=panel,
                           activeforeground=self.COLORS["text"], selectcolor=self.COLORS["surface"],
                           highlightbackground=panel, highlightcolor=self.COLORS["primary"]
                           ).pack(anchor="w", padx=17, pady=2)

        checkbox("Keep dock open", self.pinned, self._set_pinned)
        edge_row = tk.Frame(window, bg=panel)
        edge_row.pack(fill="x", padx=20, pady=6)
        tk.Label(edge_row, text="Open at top edge", bg=panel,
                 fg=self.COLORS["text"]).pack(side="left", padx=(0, 8))
        options = {label: mode for mode, label in self.EDGE_REVEAL_OPTIONS.items()
                   if mode != "shortcut" or self._reveal_hotkey_available()}
        selector = ttk.Combobox(edge_row, state="readonly", values=tuple(options))
        selector.set(self.EDGE_REVEAL_OPTIONS[self._effective_edge_reveal_mode()])
        selector.pack(side="left", fill="x", expand=True)
        selector.bind("<<ComboboxSelected>>",
                      lambda _event: self._set_edge_reveal_mode(options[selector.get()]))
        checkbox("Start TopDock with Linux", is_in_startup(), lambda _value: self.toggle_startup())
        checkbox("Compact window cards", self.compact_mode, self._set_compact_mode)
        checkbox("Show window search", self.show_window_search, self._set_search_visibility)

        def settings_button(text, command, foreground=None, background=None):
            tk.Button(window, text=text, command=command, relief="flat", cursor="hand2",
                      fg=foreground or self.COLORS["text"], bg=background or self.COLORS["surface"],
                      highlightbackground=self.COLORS["border"], highlightcolor=self.COLORS["primary"],
                      padx=10, pady=5).pack(fill="x", padx=19, pady=(5, 0))

        settings_button("Open Zoom Clipboard", self._open_zoom_clipboard, background="#243345")
        self.zoom_status = tk.Label(window, bg=panel, fg=self.COLORS["muted"], wraplength=285, justify="left")
        self.zoom_divider = tk.Frame(window, bg=self.COLORS["border"], height=1)
        self.zoom_divider.pack(fill="x", padx=20, pady=(8, 10))
        tk.Label(window, text="Ctrl + Alt + Space  ·  Show or hide TopDock\n"
                              "PASTE  ·  Type host clipboard into VDI\n"
                              "AUTO  ·  Start, stop, or select click area\n"
                              "SHOT  ·  Drag any screen area to copy it\n"
                              "Alt + 1–9  ·  Switch windows when focused\n"
                              "Middle-click  ·  Close a window",
                 justify="left", bg=panel, fg=self.COLORS["muted"],
                 font=("Inter", 9)).pack(anchor="w", padx=20)
        choices = tk.Frame(window, bg=panel)
        choices.pack(anchor="w", padx=17, pady=(5, 0))
        tk.Label(choices, text="Quick buttons", bg=panel, fg=self.COLORS["muted"]).pack(side="left", padx=(3, 5))
        for key, label in (("paste", "Paste"), ("shot", "Shot"), ("auto", "Auto")):
            visible = tk.BooleanVar(window, value=key not in self.quick_hidden)
            tk.Checkbutton(choices, text=label, variable=visible,
                           command=lambda action=key, state=visible: self._toggle_quick_action(action, state),
                           bg=panel, fg=self.COLORS["text"], selectcolor=self.COLORS["surface"],
                           activebackground=panel, activeforeground=self.COLORS["text"],
                           highlightbackground=panel, highlightcolor=self.COLORS["primary"]).pack(side="left")
        settings_button("Preview local clipboard", self.show_clipboard_preview)
        settings_button("Collapse to circle", self.collapse_dock)
        settings_button("Exit TopDock", self.exit, "#fca5a5", "#36242c")
        tk.Label(window, text="Made with ♥ by Aditya Rathee", font=("Inter", 9, "bold"),
                 bg=panel, fg="#d8b4fe").pack(pady=(10, 12))

        window.update_idletasks()
        panel_width = max(320, window.winfo_reqwidth())
        panel_height = window.winfo_reqheight()
        settings_y = min(self.shown_y + self.HEIGHT + 8, max(0, self.root.winfo_screenheight() - panel_height))
        window.minsize(panel_width, 1)
        window.geometry(f"+{max(0, self.x + self.width - panel_width)}+{settings_y}")
        window.protocol("WM_DELETE_WINDOW", close_settings)
        window.bind("<Escape>", close_settings)

    def _drain_ui_queue(self):
        while True:
            try:
                callback = self.ui_queue.get_nowait()
            except Empty:
                break
            callback()
        self.root.after(50, self._drain_ui_queue)

    def _open_search(self, _event=None):
        if not self.show_window_search or self.capture_busy or self.settings_window:
            return
        self.reveal()
        self.search_open = True
        self.search_panel.place(relwidth=1, relheight=1)
        self.search_panel.lift()
        self.search_entry.focus_force()
        return "break"

    def _close_search(self, _event=None):
        if self.search_open:
            self.search_open = False
            self.search_panel.place_forget()
            self.search_input.set("")
        return "break"

    def _set_search_query(self, query):
        self.search_query = query.strip()
        self._refresh_windows(schedule=False)

    def _set_search_visibility(self, visible):
        self.show_window_search = visible
        if not visible:
            self._close_search()
        self._apply_quick_action_layout()
        self._save_ui_settings()

    def _set_compact_mode(self, compact):
        self.compact_mode = compact
        self._update_window_scrollregion()
        self._save_ui_settings()

    def toggle_pin(self):
        self._set_pinned(not self.pinned)

    def _set_pinned(self, pinned):
        self.pinned = pinned
        self.last_inside = time.monotonic()
        self._save_ui_settings()
        self._update_control_states()
        self._set_status("Dock pinned open" if pinned else "Dock auto-hide enabled", "info")

    def _update_control_states(self):
        self.pin_button.configure(style="TopDock.PinOn.TButton" if self.pinned else "TopDock.Action.TButton")
        if hasattr(self, "clicker"):
            running = self.clicker.clicking
            self.auto_button.configure(text="ON" if running else "AUTO",
                                       style="TopDock.AutoOn.TButton" if running else "TopDock.Action.TButton")

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

    def _set_edge_reveal_mode(self, mode):
        self.edge_reveal_mode = mode
        self.edge_entered_at = None
        self._save_ui_settings()

    def _reveal_hotkey_available(self):
        return self.hotkey_listener is not None and self.hotkey_listener.is_alive()

    def _effective_edge_reveal_mode(self):
        if self.edge_reveal_mode == "shortcut" and not self._reveal_hotkey_available():
            return "delayed"
        return self.edge_reveal_mode

    def _track_pointer(self):
        if (self.capture_busy or self.settings_window or self.search_open
                or self.click_area_pending or self.clicker.selection_window or self.auto_menu.winfo_ismapped()):
            self.edge_entered_at = None
            self.root.after(70, self._track_pointer)
            return
        try:
            pointer_x, pointer_y = self.root.winfo_pointerxy()
        except tk.TclError:
            return

        now = time.monotonic()
        mode = self._effective_edge_reveal_mode()
        if 0 <= pointer_y <= 2 and mode != "shortcut":
            if self.is_shown and not self.collapsed:
                self.last_inside = now
            else:
                if self.edge_entered_at is None:
                    self.edge_entered_at = now
                if mode == "immediate" or now - self.edge_entered_at >= self.EDGE_REVEAL_DELAY:
                    self.reveal()
        else:
            self.edge_entered_at = None
            if self.is_shown and not self.collapsed:
                inside = (self.x <= pointer_x <= self.x + self.width
                          and self.shown_y <= pointer_y <= self.shown_y + self.HEIGHT + 4)
                if inside:
                    self.last_inside = now
                elif not self.pinned and now - self.last_inside > 0.8:
                    self.hide()

        self.root.after(70, self._track_pointer)

    def _toggle_dock(self):
        if self.capture_busy:
            return
        if self.is_shown and not self.collapsed and not self.settings_window:
            self.hide()
        else:
            self.reveal()

    def reveal(self):
        if self.capture_busy:
            return
        self.edge_entered_at = None
        self.last_inside = time.monotonic()
        if self.collapsed:
            self.drag_moved = False
            self.expand_dock()
            return
        self.is_shown = True
        self._animate_to(self.shown_y)

    def hide(self, force=False):
        if self.collapsed:
            return
        if self.pinned and not force:
            return
        self._close_search()
        self.is_shown = False
        self.edge_entered_at = None
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
        width, height = (60, 60) if self.collapsed else (self.width, self.HEIGHT)
        self.root.geometry(f"{width}x{height}+{self.x}{y_position}")

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
    if "--version" in sys.argv:
        print(f"TopDock {LinuxTopDock.VERSION}")
        return 0
    if not IS_LINUX:
        print("Linux TopDock must be run from a Linux desktop session.")
        return 1

    if "--portable-test" in sys.argv:
        from portable_checks import run
        run()
        return 0

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
