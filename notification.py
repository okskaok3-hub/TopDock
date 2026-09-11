# Notification Overlay Module
# Always-on-top notification display

import tkinter as tk
from datetime import datetime

from platform_utils import IS_WINDOWS
from settings import config


class NotificationCard(tk.Toplevel):
    """A compact notification card window."""

    COLORS = {
        'bg': '#1e1e2e',
        'card_bg': '#2a2a3e',
        'border': '#3d3d5c',
        'accent': '#7c3aed',
        'text': '#f8fafc',
        'text_dim': '#94a3b8',
        'close_hover': '#ef4444',
    }

    APP_COLORS = {
        'Teams': '#5b5fc7', 'Outlook': '#0078d4', 'Slack': '#611f69',
        'System': '#7c3aed', 'VDI Toolkit': '#7c3aed', 'Clicker': '#10b981',
        'Paste': '#3b82f6'
    }

    def __init__(
        self,
        parent,
        notification,
        on_dismiss=None,
        index=0,
        duration=5000,
        position='top-right',
        overlay_enabled=True,
    ):
        super().__init__(parent)

        self.notification = notification
        self.on_dismiss = on_dismiss
        self.index = index
        self.duration = duration
        self.position = position
        self.overlay_enabled = bool(overlay_enabled)
        self.dismiss_timer = None
        self.reassert_timer = None

        self.overrideredirect(True)
        self.attributes('-topmost', self.overlay_enabled)
        self.attributes('-alpha', 0.95)
        self.focusmodel('passive')
        self.configure(bg=self.COLORS['bg'])

        self.card_width = 320
        self.card_height = 70

        self._create_ui()
        self._position()
        self._apply_windows_overlay_style()

        if duration > 0:
            self.dismiss_timer = self.after(duration, self.dismiss)

        if self.overlay_enabled:
            self._schedule_overlay_reassert()

    def _create_ui(self):
        """Create card UI."""
        card = tk.Frame(self, bg=self.COLORS['card_bg'], padx=12, pady=8)
        card.pack(fill='both', expand=True, padx=2, pady=2)

        self.configure(highlightbackground=self.COLORS['border'], highlightthickness=1)

        # Header
        header = tk.Frame(card, bg=self.COLORS['card_bg'])
        header.pack(fill='x', pady=(0, 4))

        app = self.notification.get('app', 'System')
        color = self.APP_COLORS.get(app, self.COLORS['accent'])

        tk.Label(header, text=app, bg=self.COLORS['card_bg'], fg=color,
                 font=('Segoe UI', 9, 'bold')).pack(side='left')

        close_btn = tk.Label(header, text='✕', bg=self.COLORS['card_bg'],
                            fg=self.COLORS['text_dim'], font=('Segoe UI', 9), cursor='hand2')
        close_btn.pack(side='right')
        close_btn.bind('<Button-1>', lambda e: self.dismiss())
        close_btn.bind('<Enter>', lambda e: close_btn.config(fg=self.COLORS['close_hover']))
        close_btn.bind('<Leave>', lambda e: close_btn.config(fg=self.COLORS['text_dim']))

        ts = datetime.now().strftime('%I:%M %p').lstrip('0')
        tk.Label(header, text=ts, bg=self.COLORS['card_bg'], fg=self.COLORS['text_dim'],
                 font=('Segoe UI', 8)).pack(side='right', padx=(0, 8))

        # Title
        tk.Label(card, text=self.notification.get('title', ''), bg=self.COLORS['card_bg'],
                 fg=self.COLORS['text'], font=('Segoe UI', 10, 'bold'),
                 anchor='w').pack(fill='x')

        # Message
        msg = self.notification.get('message', '')
        if msg:
            if len(msg) > 60:
                msg = msg[:57] + '...'
            tk.Label(card, text=msg, bg=self.COLORS['card_bg'], fg=self.COLORS['text_dim'],
                     font=('Segoe UI', 9), anchor='w').pack(fill='x')

    def _monitor_bounds(self):
        """Return the monitor under the mouse, including its full-screen area."""
        if IS_WINDOWS:
            try:
                import win32api
                import win32con

                cursor_x, cursor_y = win32api.GetCursorPos()
                monitor = win32api.MonitorFromPoint(
                    (cursor_x, cursor_y), win32con.MONITOR_DEFAULTTONEAREST
                )
                info = win32api.GetMonitorInfo(monitor)
                return info['Monitor']
            except Exception:
                # Tk's screen metrics remain a useful fallback when pywin32 is
                # unavailable or the window is being created during logon.
                pass

        return (0, 0, self.winfo_screenwidth(), self.winfo_screenheight())

    def _position(self):
        """Position the card on the monitor containing the mouse/VDI session."""
        left, top, right, bottom = self._monitor_bounds()

        if self.position == 'top-left':
            x = left + 15
            y = top + 40 + self.index * (self.card_height + 8)
        elif self.position == 'bottom-right':
            x = right - self.card_width - 15
            y = bottom - self.card_height - 40 - self.index * (self.card_height + 8)
        elif self.position == 'bottom-left':
            x = left + 15
            y = bottom - self.card_height - 40 - self.index * (self.card_height + 8)
        else:
            x = right - self.card_width - 15
            y = top + 40 + self.index * (self.card_height + 8)

        self.geometry(f"{self.card_width}x{self.card_height}+{x}+{y}")

    def _apply_windows_overlay_style(self):
        """Make the card a non-activating native Windows overlay."""
        if not IS_WINDOWS:
            return

        try:
            import win32con
            import win32gui

            hwnd = self.winfo_id()
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_TOOLWINDOW
            if self.overlay_enabled:
                ex_style |= win32con.WS_EX_NOACTIVATE
                ex_style |= win32con.WS_EX_TOPMOST
            else:
                ex_style &= ~win32con.WS_EX_NOACTIVATE
                ex_style &= ~win32con.WS_EX_TOPMOST
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

            insert_after = win32con.HWND_TOPMOST if self.overlay_enabled else win32con.HWND_NOTOPMOST
            flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            flags |= win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED
            win32gui.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)
        except Exception:
            # The Tk implementation still works on Windows without pywin32.
            pass

    def _schedule_overlay_reassert(self):
        """Keep the card above borderless/full-screen VDI windows without focus."""
        if self.overlay_enabled and self.winfo_exists():
            self.reassert_timer = self.after(1000, self._reassert_overlay)

    def _reassert_overlay(self):
        self.reassert_timer = None
        if self.overlay_enabled and self.winfo_exists():
            self._apply_windows_overlay_style()
            self._schedule_overlay_reassert()

    def set_overlay_mode(self, enabled):
        self.overlay_enabled = bool(enabled)
        self.attributes('-topmost', self.overlay_enabled)
        self._apply_windows_overlay_style()
        if self.overlay_enabled and not self.reassert_timer:
            self._schedule_overlay_reassert()
        elif not self.overlay_enabled and self.reassert_timer:
            self.after_cancel(self.reassert_timer)
            self.reassert_timer = None

    def update_position(self, index, position=None):
        self.index = index
        if position:
            self.position = position
        self._position()

    def dismiss(self):
        if self.dismiss_timer:
            self.after_cancel(self.dismiss_timer)
        if self.reassert_timer:
            self.after_cancel(self.reassert_timer)
            self.reassert_timer = None
        if self.on_dismiss:
            self.on_dismiss(self)
        try:
            self.destroy()
        except:
            pass


class NotificationManager:
    """Manages notification cards."""

    def __init__(self, root):
        self.root = root
        self.cards = []
        self.max_cards = 5
        self.duration = config.get('notify_duration', 5) * 1000
        self.enabled = config.get('notify_enabled', True)
        self.overlay_enabled = config.get('notify_overlay', True)
        self.position = config.get('notify_position', 'top-right')

    def show(self, app, title, message=''):
        """Show a notification."""
        if not self.enabled:
            return

        while len(self.cards) >= self.max_cards:
            old = self.cards.pop(0)
            try:
                old.dismiss()
            except:
                pass

        notif = {'app': app, 'title': title, 'message': message}
        card = NotificationCard(
            self.root, notif,
            on_dismiss=self._on_dismiss,
            index=len(self.cards),
            duration=self.duration,
            position=self.position,
            overlay_enabled=self.overlay_enabled,
        )
        self.cards.append(card)

    def _on_dismiss(self, card):
        if card in self.cards:
            self.cards.remove(card)
            self._reflow_cards()

    def _reflow_cards(self):
        for i, card in enumerate(self.cards):
            try:
                card.update_position(i, self.position)
            except Exception:
                pass

    def clear_all(self):
        for card in self.cards[:]:
            try:
                card.dismiss()
            except:
                pass
        self.cards.clear()

    def toggle(self):
        self.set_enabled(not self.enabled)
        return self.enabled

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        config.set('notify_enabled', self.enabled)

    def set_overlay(self, enabled):
        self.overlay_enabled = bool(enabled)
        config.set('notify_overlay', self.overlay_enabled)
        for card in self.cards[:]:
            try:
                card.set_overlay_mode(self.overlay_enabled)
            except Exception:
                pass

    def set_duration(self, duration_seconds):
        duration_seconds = max(1, int(duration_seconds))
        self.duration = duration_seconds * 1000
        config.set('notify_duration', duration_seconds)

    def set_position(self, position):
        valid_positions = {'top-right', 'top-left', 'bottom-right', 'bottom-left'}
        if position not in valid_positions:
            raise ValueError(f"Invalid notification position: {position}")
        self.position = position
        config.set('notify_position', position)
        self._reflow_cards()
