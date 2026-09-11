# VDI Toolkit - Desktop UI
# Colorful, accessible control center for Windows/Linux

import os
import subprocess
import tkinter as tk
from tkinter import ttk

from settings import config, PASTE_MODES
from platform_utils import IS_WINDOWS, IS_LINUX, IS_MAC, is_in_startup, toggle_startup, get_config_dir


class ToolkitUI:
    def __init__(self, root, clipboard, clicker, ai_assistant, notifier, on_exit):
        self.root = root
        self.clipboard = clipboard
        self.clicker = clicker
        self.ai_assistant = ai_assistant
        self.notifier = notifier
        self.on_exit = on_exit

        self.colors = {
            "bg": "#0f1226",
            "panel": "#151a33",
            "panel_alt": "#1b2142",
            "card": "#1f254a",
            "accent": "#4ecdc4",
            "accent2": "#ff6b6b",
            "accent3": "#ffe66d",
            "text": "#f8fafc",
            "text_dim": "#cbd5e1",
            "muted": "#94a3b8",
            "danger": "#ef4444",
            "success": "#10b981",
        }

        self.root.title("VDI Toolkit")
        self.root.geometry("980x640")
        self.root.minsize(900, 600)
        self.root.configure(bg=self.colors["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self._build_style()
        self._build_layout()
        self._load_from_config()
        self._refresh_status()

    def _build_style(self):
        # ttk is used only where default styling is acceptable; tk is used for vivid colors
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

    def _build_layout(self):
        # Top bar
        top = tk.Frame(self.root, bg=self.colors["panel"])
        top.pack(side="top", fill="x")

        title = tk.Label(
            top, text="VDI Toolkit",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=("Segoe UI", 16, "bold")
        )
        title.pack(side="left", padx=16, pady=12)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(
            top, textvariable=self.status_var,
            bg=self.colors["panel"],
            fg=self.colors["text_dim"],
            font=("Segoe UI", 10)
        )
        self.status_label.pack(side="left", padx=12)

        quit_btn = tk.Button(
            top, text="Exit",
            bg=self.colors["danger"],
            fg="white",
            activebackground=self.colors["accent2"],
            relief="flat",
            command=self._exit_app
        )
        quit_btn.pack(side="right", padx=16, pady=10)

        # Main body
        body = tk.Frame(self.root, bg=self.colors["bg"])
        body.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(body, bg=self.colors["panel"], width=200)
        sidebar.pack(side="left", fill="y")

        self.section_var = tk.StringVar(value="Dashboard")

        def add_nav(name, color):
            btn = tk.Button(
                sidebar, text=name,
                bg=self.colors["panel"],
                fg=self.colors["text"],
                activebackground=color,
                activeforeground="black",
                relief="flat",
                font=("Segoe UI", 11, "bold"),
                command=lambda: self._show_section(name)
            )
            btn.pack(fill="x", padx=12, pady=6)

        add_nav("Dashboard", self.colors["accent"])
        add_nav("Clipboard", self.colors["accent3"])
        add_nav("Clicker", self.colors["accent2"])
        add_nav("AI", self.colors["accent"])
        add_nav("Notifications", self.colors["accent"])
        add_nav("Advanced", self.colors["accent3"])

        # Content area
        self.content = tk.Frame(body, bg=self.colors["bg"])
        self.content.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        self.sections = {}
        self.sections["Dashboard"] = self._build_dashboard(self.content)
        self.sections["Clipboard"] = self._build_clipboard(self.content)
        self.sections["Clicker"] = self._build_clicker(self.content)
        self.sections["AI"] = self._build_ai(self.content)
        self.sections["Notifications"] = self._build_notifications(self.content)
        self.sections["Advanced"] = self._build_advanced(self.content)

        self._show_section("Dashboard")

    def _section_frame(self, parent, title):
        frame = tk.Frame(parent, bg=self.colors["panel_alt"])
        header = tk.Label(
            frame, text=title,
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
            font=("Segoe UI", 14, "bold")
        )
        header.pack(anchor="w", padx=16, pady=(12, 6))
        return frame

    def _build_dashboard(self, parent):
        frame = self._section_frame(parent, "Overview")

        card_wrap = tk.Frame(frame, bg=self.colors["panel_alt"])
        card_wrap.pack(fill="x", padx=16, pady=8)

        self.paste_status_var = tk.StringVar(value="Paste: Ready")
        self.clicker_status_var = tk.StringVar(value="Clicker: No Area")
        self.ai_status_var = tk.StringVar(value="AI: Ready")
        self.notify_status_var = tk.StringVar(value="Notifications: On")

        self._card(card_wrap, "Clipboard", self.paste_status_var, self.colors["accent3"])
        self._card(card_wrap, "Auto Clicker", self.clicker_status_var, self.colors["accent2"])
        self._card(card_wrap, "AI Screenshot", self.ai_status_var, self.colors["accent"])
        self._card(card_wrap, "Notifications", self.notify_status_var, self.colors["accent"])

        actions = tk.Frame(frame, bg=self.colors["panel_alt"])
        actions.pack(fill="x", padx=16, pady=(6, 12))

        self._action_btn(actions, "Paste Now", self.clipboard.trigger_paste, self.colors["accent3"])
        self._action_btn(actions, "Select Click Area", self.clicker.select_area, self.colors["accent2"])
        self._action_btn(actions, "Start/Stop Clicker", self.clicker.toggle, self.colors["accent2"])
        self._action_btn(actions, "Capture && Ask AI", self.ai_assistant.capture_and_ask, self.colors["accent"])
        self._action_btn(actions, "Test Notification", self._test_notification, self.colors["accent"])

        frame.pack(fill="both", expand=True)
        return frame

    def _build_clipboard(self, parent):
        frame = self._section_frame(parent, "Clipboard Paste")

        modes = tk.Frame(frame, bg=self.colors["panel_alt"])
        modes.pack(fill="x", padx=16, pady=10)

        tk.Label(modes, text="Paste Mode", bg=self.colors["panel_alt"],
                 fg=self.colors["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.paste_mode_var = tk.StringVar()
        for mode in ("fast", "safe", "ultra_safe"):
            rb = tk.Radiobutton(
                modes, text=mode.replace("_", " ").title(),
                variable=self.paste_mode_var, value=mode,
                bg=self.colors["panel_alt"], fg=self.colors["text"],
                activebackground=self.colors["panel_alt"],
                selectcolor=self.colors["panel"],
                command=self._apply_paste_mode
            )
            rb.pack(anchor="w", pady=2)

        delays = tk.Frame(frame, bg=self.colors["panel_alt"])
        delays.pack(fill="x", padx=16, pady=10)

        tk.Label(delays, text="Delays (seconds)", bg=self.colors["panel_alt"],
                 fg=self.colors["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.char_delay_var = tk.DoubleVar()
        self.press_duration_var = tk.DoubleVar()
        self._labeled_entry(delays, "Character Delay", self.char_delay_var)
        self._labeled_entry(delays, "Press Duration", self.press_duration_var)

        self.trim_trailing_whitespace_var = tk.BooleanVar()
        tk.Checkbutton(
            delays,
            text="Trim trailing spaces/newlines",
            variable=self.trim_trailing_whitespace_var,
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
            activebackground=self.colors["panel_alt"],
            selectcolor=self.colors["panel"],
        ).pack(anchor="w", pady=(6, 0))

        hotkey = tk.Frame(frame, bg=self.colors["panel_alt"])
        hotkey.pack(fill="x", padx=16, pady=10)
        tk.Label(hotkey, text="Hotkey (keyboard format)", bg=self.colors["panel_alt"],
                 fg=self.colors["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.paste_hotkey_var = tk.StringVar()
        self._labeled_entry(hotkey, "Paste Hotkey", self.paste_hotkey_var)
        self.pause_hotkey_var = tk.StringVar()
        self._labeled_entry(hotkey, "Pause/Resume Hotkey", self.pause_hotkey_var)

        actions = tk.Frame(frame, bg=self.colors["panel_alt"])
        actions.pack(fill="x", padx=16, pady=(4, 8))
        tk.Button(
            actions,
            text="Pause / Resume",
            bg=self.colors["accent"],
            fg="black",
            relief="flat",
            command=self._pause_resume_paste,
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            actions,
            text="Cancel Paste",
            bg=self.colors["danger"],
            fg="white",
            relief="flat",
            command=self._cancel_paste,
        ).pack(side="left")

        apply_btn = tk.Button(
            frame, text="Apply Clipboard Settings",
            bg=self.colors["accent3"], fg="black",
            activebackground=self.colors["accent"],
            relief="flat", command=self._apply_clipboard_settings
        )
        apply_btn.pack(anchor="e", padx=16, pady=12)

        frame.pack(fill="both", expand=True)
        return frame

    def _build_clicker(self, parent):
        frame = self._section_frame(parent, "Auto Clicker")

        status = tk.Frame(frame, bg=self.colors["panel_alt"])
        status.pack(fill="x", padx=16, pady=10)
        self.clicker_area_var = tk.StringVar(value="Area: Not selected")
        tk.Label(status, textvariable=self.clicker_area_var, bg=self.colors["panel_alt"],
                 fg=self.colors["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w")

        actions = tk.Frame(frame, bg=self.colors["panel_alt"])
        actions.pack(fill="x", padx=16, pady=10)
        self._action_btn(actions, "Select Area", self.clicker.select_area, self.colors["accent2"])
        self._action_btn(actions, "Start/Stop", self.clicker.toggle, self.colors["accent2"])

        delays = tk.Frame(frame, bg=self.colors["panel_alt"])
        delays.pack(fill="x", padx=16, pady=10)
        tk.Label(delays, text="Click Delay (seconds)", bg=self.colors["panel_alt"],
                 fg=self.colors["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.delay_min_var = tk.DoubleVar()
        self.delay_max_var = tk.DoubleVar()
        self._labeled_entry(delays, "Minimum Delay", self.delay_min_var)
        self._labeled_entry(delays, "Maximum Delay", self.delay_max_var)

        hotkey = tk.Frame(frame, bg=self.colors["panel_alt"])
        hotkey.pack(fill="x", padx=16, pady=10)
        tk.Label(hotkey, text="Hotkey (keyboard format)", bg=self.colors["panel_alt"],
                 fg=self.colors["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.clicker_hotkey_var = tk.StringVar()
        self._labeled_entry(hotkey, "Clicker Hotkey", self.clicker_hotkey_var)

        apply_btn = tk.Button(
            frame, text="Apply Clicker Settings",
            bg=self.colors["accent2"], fg="black",
            activebackground=self.colors["accent"],
            relief="flat", command=self._apply_clicker_settings
        )
        apply_btn.pack(anchor="e", padx=16, pady=12)

        frame.pack(fill="both", expand=True)
        return frame

    def _build_notifications(self, parent):
        frame = self._section_frame(parent, "Notifications")

        controls = tk.Frame(frame, bg=self.colors["panel_alt"])
        controls.pack(fill="x", padx=16, pady=10)

        self.notify_enabled_var = tk.BooleanVar()
        enable_cb = tk.Checkbutton(
            controls, text="Enable Notifications",
            variable=self.notify_enabled_var,
            bg=self.colors["panel_alt"], fg=self.colors["text"],
            activebackground=self.colors["panel_alt"],
            selectcolor=self.colors["panel"],
            command=self._apply_notification_settings
        )
        enable_cb.pack(anchor="w")

        self.notify_overlay_var = tk.BooleanVar()
        overlay_cb = tk.Checkbutton(
            controls,
            text="Float above full-screen VDI windows (Windows)",
            variable=self.notify_overlay_var,
            bg=self.colors["panel_alt"], fg=self.colors["text"],
            activebackground=self.colors["panel_alt"],
            activeforeground=self.colors["text"],
            selectcolor=self.colors["panel"],
            command=self._apply_notification_settings,
        )
        overlay_cb.pack(anchor="w", pady=(4, 0))

        self.notify_duration_var = tk.IntVar()
        self._labeled_entry(controls, "Duration (seconds)", self.notify_duration_var)

        tk.Label(controls, text="Position", bg=self.colors["panel_alt"],
                 fg=self.colors["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 0))
        self.notify_position_var = tk.StringVar()
        pos_menu = ttk.Combobox(
            controls, textvariable=self.notify_position_var,
            values=["top-right", "top-left", "bottom-right", "bottom-left"],
            state="readonly"
        )
        pos_menu.pack(anchor="w", pady=4)
        pos_menu.bind("<<ComboboxSelected>>", lambda e: self._apply_notification_settings())

        actions = tk.Frame(frame, bg=self.colors["panel_alt"])
        actions.pack(fill="x", padx=16, pady=10)
        self._action_btn(actions, "Test Notification", self._test_notification, self.colors["accent"])
        self._action_btn(actions, "Clear All", self.notifier.clear_all, self.colors["accent"])

        apply_btn = tk.Button(
            frame, text="Apply Notification Settings",
            bg=self.colors["accent"], fg="black",
            activebackground=self.colors["accent3"],
            relief="flat", command=self._apply_notification_settings
        )
        apply_btn.pack(anchor="e", padx=16, pady=12)

        frame.pack(fill="both", expand=True)
        return frame

    def _build_ai(self, parent):
        frame = self._section_frame(parent, "AI Screenshot")

        status = tk.Frame(frame, bg=self.colors["panel_alt"])
        status.pack(fill="x", padx=16, pady=10)
        self.ai_provider_status_var = tk.StringVar(value="Provider: OPENAI")
        self.ai_hotkey_status_var = tk.StringVar(value="Hotkey: CTRL+SHIFT+A")
        tk.Label(
            status,
            textvariable=self.ai_provider_status_var,
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        tk.Label(
            status,
            textvariable=self.ai_hotkey_status_var,
            bg=self.colors["panel_alt"],
            fg=self.colors["text_dim"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 0))

        actions = tk.Frame(frame, bg=self.colors["panel_alt"])
        actions.pack(fill="x", padx=16, pady=10)
        self._action_btn(actions, "Capture && Ask", self.ai_assistant.capture_and_ask, self.colors["accent"])
        self._action_btn(actions, "Open Compact Settings", self.ai_assistant.open_settings_dialog, self.colors["accent3"])

        controls = tk.Frame(frame, bg=self.colors["panel_alt"])
        controls.pack(fill="both", expand=True, padx=16, pady=10)

        tk.Label(
            controls,
            text="Provider",
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        self.ai_provider_var = tk.StringVar()
        provider_menu = ttk.Combobox(
            controls,
            textvariable=self.ai_provider_var,
            values=["openai", "gemini"],
            state="readonly",
        )
        provider_menu.pack(anchor="w", pady=4)

        self.ai_hotkey_var = tk.StringVar()
        self._labeled_entry(controls, "AI Hotkey", self.ai_hotkey_var)

        self.openai_model_var = tk.StringVar()
        self._labeled_entry(controls, "OpenAI Model", self.openai_model_var)
        self.openai_api_key_var = tk.StringVar()
        self._labeled_entry(controls, "OpenAI API Key", self.openai_api_key_var, show="*")

        self.gemini_model_var = tk.StringVar()
        self._labeled_entry(controls, "Gemini Model", self.gemini_model_var)
        self.gemini_api_key_var = tk.StringVar()
        self._labeled_entry(controls, "Gemini API Key", self.gemini_api_key_var, show="*")

        tk.Label(
            controls,
            text="Saved Prompt",
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(10, 0))
        self.ai_system_prompt_box = tk.Text(
            controls,
            height=10,
            wrap="word",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            relief="flat",
            insertbackground=self.colors["text"],
        )
        self.ai_system_prompt_box.pack(fill="both", expand=True, pady=6)

        apply_btn = tk.Button(
            frame,
            text="Apply AI Settings",
            bg=self.colors["accent"],
            fg="black",
            activebackground=self.colors["accent3"],
            relief="flat",
            command=self._apply_ai_settings,
        )
        apply_btn.pack(anchor="e", padx=16, pady=12)

        frame.pack(fill="both", expand=True)
        return frame

    def _build_advanced(self, parent):
        frame = self._section_frame(parent, "Advanced Configuration")

        controls = tk.Frame(frame, bg=self.colors["panel_alt"])
        controls.pack(fill="x", padx=16, pady=10)

        self.startup_var = tk.BooleanVar()
        startup_cb = tk.Checkbutton(
            controls, text="Start with Linux" if IS_LINUX else "Start with Windows",
            variable=self.startup_var,
            bg=self.colors["panel_alt"], fg=self.colors["text"],
            activebackground=self.colors["panel_alt"],
            selectcolor=self.colors["panel"],
            command=self._toggle_startup
        )
        startup_cb.pack(anchor="w")

        config_path = str(get_config_dir())
        tk.Label(controls, text=f"Config Folder: {config_path}", bg=self.colors["panel_alt"],
                 fg=self.colors["text_dim"], font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 4))

        self._action_btn(controls, "Open Config Folder", self._open_config_folder, self.colors["accent3"])
        self._action_btn(controls, "Reset to Defaults", self._reset_defaults, self.colors["accent2"])

        frame.pack(fill="both", expand=True)
        return frame

    def _card(self, parent, title, value_var, accent):
        card = tk.Frame(parent, bg=self.colors["card"])
        card.pack(side="left", padx=8, pady=6, expand=True, fill="both")
        bar = tk.Frame(card, bg=accent, height=4)
        bar.pack(fill="x")
        tk.Label(card, text=title, bg=self.colors["card"],
                 fg=self.colors["text_dim"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
        tk.Label(card, textvariable=value_var, bg=self.colors["card"],
                 fg=self.colors["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(2, 10))

    def _action_btn(self, parent, text, cmd, color):
        btn = tk.Button(
            parent, text=text,
            bg=color, fg="black",
            activebackground=self.colors["accent3"],
            relief="flat", command=cmd
        )
        btn.pack(side="left", padx=6, pady=6)

    def _labeled_entry(self, parent, label, var, show=None):
        row = tk.Frame(parent, bg=self.colors["panel_alt"])
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=self.colors["panel_alt"],
                 fg=self.colors["text_dim"], font=("Segoe UI", 10)).pack(side="left")
        entry = tk.Entry(row, textvariable=var, bg=self.colors["panel"],
                         fg=self.colors["text"], relief="flat", width=12, show=show)
        entry.pack(side="right")

    def _show_section(self, name):
        for sec in self.sections.values():
            sec.pack_forget()
        self.sections[name].pack(fill="both", expand=True)
        self.section_var.set(name)

    def _load_from_config(self):
        self.paste_mode_var.set(config.get("paste_mode", "safe"))
        self.char_delay_var.set(config.get("char_delay", 0.05))
        self.press_duration_var.set(config.get("press_duration", 0.02))
        self.paste_hotkey_var.set(config.get("paste_hotkey", "ctrl+shift+v"))
        self.pause_hotkey_var.set(config.get("pause_hotkey", "ctrl+shift+p"))
        self.trim_trailing_whitespace_var.set(config.get("trim_trailing_whitespace", True))

        self.delay_min_var.set(config.get("click_delay_min", 60))
        self.delay_max_var.set(config.get("click_delay_max", 60))
        self.clicker_hotkey_var.set(config.get("clicker_hotkey", "shift+alt+9"))

        self.notify_enabled_var.set(config.get("notify_enabled", True))
        self.notify_overlay_var.set(config.get("notify_overlay", True))
        self.notify_duration_var.set(config.get("notify_duration", 5))
        self.notify_position_var.set(config.get("notify_position", "top-right"))

        self.ai_provider_var.set(config.get("ai_provider", "openai"))
        self.ai_hotkey_var.set(config.get("ai_hotkey", "ctrl+shift+a"))
        self.openai_model_var.set(config.get("openai_model", "gpt-4.1-mini"))
        self.openai_api_key_var.set(config.get("openai_api_key", ""))
        self.gemini_model_var.set(config.get("gemini_model", "gemini-2.5-flash"))
        self.gemini_api_key_var.set(config.get("gemini_api_key", ""))
        self.ai_system_prompt_box.delete("1.0", "end")
        self.ai_system_prompt_box.insert("1.0", config.get("ai_system_prompt", ""))

        self.startup_var.set(is_in_startup())

    def _apply_paste_mode(self):
        mode = self.paste_mode_var.get()
        self.clipboard.set_mode(mode)
        self._load_from_config()

    def _apply_clipboard_settings(self):
        try:
            char_delay = float(self.char_delay_var.get())
            press_duration = float(self.press_duration_var.get())
            hotkey = self.paste_hotkey_var.get().strip().lower()
            if char_delay <= 0 or press_duration <= 0:
                raise ValueError("Delays must be positive")

            self.clipboard.update_settings(
                mode=self.paste_mode_var.get(),
                char_delay=char_delay,
                press_duration=press_duration,
                hotkey=hotkey or None,
                pause_hotkey=self.pause_hotkey_var.get().strip().lower() or None,
                trim_trailing_whitespace=bool(self.trim_trailing_whitespace_var.get()),
            )

            self._set_status("Clipboard settings applied", "success")
        except Exception as e:
            self._set_status(f"Clipboard settings error: {e}", "error")

    def _pause_resume_paste(self):
        if not self.clipboard.pause_resume():
            self._set_status("No paste is currently running", "warning")

    def _cancel_paste(self):
        if not self.clipboard.cancel_paste():
            self._set_status("No paste is currently running", "warning")

    def _apply_clicker_settings(self):
        try:
            dmin = float(self.delay_min_var.get())
            dmax = float(self.delay_max_var.get())
            if dmin <= 0 or dmax <= 0 or dmax < dmin:
                raise ValueError("Delay range invalid")
            hotkey = self.clicker_hotkey_var.get().strip().lower()

            self.clicker.update_settings(
                delay_min=dmin,
                delay_max=dmax,
                hotkey=hotkey or None,
            )
            self._set_status("Clicker settings applied", "success")
        except Exception as e:
            self._set_status(f"Clicker settings error: {e}", "error")

    def _apply_notification_settings(self):
        try:
            enabled = bool(self.notify_enabled_var.get())
            overlay = bool(self.notify_overlay_var.get())
            duration = int(self.notify_duration_var.get())
            position = self.notify_position_var.get()

            if duration < 1:
                raise ValueError("Duration must be >= 1")

            self.notifier.set_enabled(enabled)
            self.notifier.set_overlay(overlay)
            self.notifier.set_duration(duration)
            self.notifier.set_position(position)
            self._set_status("Notification settings applied", "success")
        except Exception as e:
            self._set_status(f"Notification settings error: {e}", "error")

    def _apply_ai_settings(self):
        try:
            self.ai_assistant.update_settings(
                provider=self.ai_provider_var.get(),
                hotkey=self.ai_hotkey_var.get().strip().lower() or None,
                system_prompt=self.ai_system_prompt_box.get("1.0", "end").strip(),
                openai_api_key=self.openai_api_key_var.get().strip(),
                openai_model=self.openai_model_var.get().strip(),
                gemini_api_key=self.gemini_api_key_var.get().strip(),
                gemini_model=self.gemini_model_var.get().strip(),
            )
            self._set_status("AI settings applied", "success")
            self._load_from_config()
        except Exception as e:
            self._set_status(f"AI settings error: {e}", "error")

    def _toggle_startup(self):
        toggle_startup()
        self.startup_var.set(is_in_startup())
        config.set("start_with_windows", self.startup_var.get())
        self._set_status("Startup setting updated", "info")

    def _open_config_folder(self):
        path = get_config_dir()
        try:
            if IS_WINDOWS:
                os.startfile(path)
            elif IS_LINUX:
                subprocess.Popen(["xdg-open", str(path)])
            elif IS_MAC:
                subprocess.Popen(["open", str(path)])
        except Exception as e:
            self._set_status(f"Open folder failed: {e}", "error")

    def _reset_defaults(self):
        defaults = config.reset_defaults()
        self._load_from_config()
        self.clipboard.reload_from_config()
        self.clicker.reload_from_config()
        self.ai_assistant.reload_from_config()
        self.ai_assistant.register_hotkeys()
        self.notifier.set_enabled(defaults.get("notify_enabled"))
        self.notifier.set_overlay(defaults.get("notify_overlay"))
        self.notifier.set_duration(defaults.get("notify_duration"))
        self.notifier.set_position(defaults.get("notify_position"))
        self._set_status("Defaults restored", "info")

    def _test_notification(self):
        self.notifier.show("VDI Toolkit", "Test Notification", "Everything is working!")

    def _set_status(self, msg, msg_type="info"):
        self.status_var.set(msg)
        if msg_type == "error":
            fg = self.colors["danger"]
        elif msg_type == "success":
            fg = self.colors["success"]
        else:
            fg = self.colors["text_dim"]
        self.status_label.config(fg=fg)

    def update_status_from_module(self, msg, msg_type="info"):
        self._set_status(msg, msg_type)

    def _refresh_status(self):
        self.paste_status_var.set(
            f"Paste: {config.get('paste_mode').title()} / {self.clipboard.get_status()}"
        )
        self.clicker_status_var.set(f"Clicker: {self.clicker.get_status()}")
        self.ai_status_var.set(f"AI: {config.get('ai_provider').upper()}")
        self.notify_status_var.set("Notifications: On" if self.notifier.enabled else "Notifications: Off")
        self.ai_provider_status_var.set(f"Provider: {config.get('ai_provider').upper()}")
        self.ai_hotkey_status_var.set(f"Hotkey: {config.get('ai_hotkey').upper()}")

        if self.clicker.selection_coords:
            x1, y1, x2, y2 = self.clicker.selection_coords
            self.clicker_area_var.set(f"Area: {x2-x1} x {y2-y1}px")
        else:
            self.clicker_area_var.set("Area: Not selected")

        self.root.after(800, self._refresh_status)

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_window(self):
        self.root.withdraw()
        try:
            self.notifier.show("VDI Toolkit", "Still running", "Access from the tray menu.")
        except Exception:
            pass

    def _exit_app(self):
        self.on_exit()
