"""X11 window discovery and activation helpers for Linux TopDock."""

from dataclasses import dataclass
import re
import shutil
import subprocess


VDI_MARKERS = (
    "citrix",
    "wfica",
    "selfservice",
    "remmina",
    "xfreerdp",
    "freerdp",
    "vmware-view",
    "vmware horizon",
    "windows app",
)


@dataclass(frozen=True)
class LinuxWindow:
    window_id: str
    desktop: int
    wm_class: str
    title: str
    application: str

    @property
    def is_vdi(self):
        haystack = f"{self.wm_class} {self.title} {self.application}".lower()
        return any(marker in haystack for marker in VDI_MARKERS)


def friendly_application(wm_class, title=""):
    """Return an application label without exposing a full document title."""
    value = (wm_class or "").split(".")[-1].strip().replace("-", " ").replace("_", " ")
    class_text = (wm_class or "").lower()
    title_text = (title or "").lower()
    known = (
        (("google-chrome", "google chrome", "chromium"), "Chrome"),
        (("brave",), "Brave"),
        (("firefox",), "Firefox"),
        (("code.code", "code-oss", "visual studio code"), "VS Code"),
        (("org.gnome.nautilus", "nautilus"), "Files"),
        (("thunar",), "Files"),
        (("konsole",), "Konsole"),
        (("gnome-terminal", "org.gnome.terminal"), "Terminal"),
        (("remmina",), "Remmina"),
        (("xfreerdp", "freerdp"), "Remote Desktop"),
        (("wfica", "citrix", "selfservice"), "Citrix Workspace"),
        (("vmware-view", "vmware horizon"), "VMware Horizon"),
        (("libreoffice",), "LibreOffice"),
        (("slack",), "Slack"),
        (("teams",), "Teams"),
    )
    for markers, name in known:
        if any(marker in class_text for marker in markers):
            return name

    if "windows app" in title_text:
        return "Windows App"

    if value:
        return " ".join(part.capitalize() for part in value.split())
    return (title or "Application").split(" — ")[0].split(" - ")[-1][:28]


def parse_wmctrl_line(line):
    parts = line.strip().split(None, 4)
    if len(parts) < 5:
        return None
    window_id, desktop_text, wm_class, _host, title = parts
    try:
        desktop = int(desktop_text)
    except ValueError:
        return None
    return LinuxWindow(
        window_id=window_id,
        desktop=desktop,
        wm_class=wm_class,
        title=title,
        application=friendly_application(wm_class, title),
    )


class X11WindowService:
    def __init__(self, own_title="TopDock Linux"):
        self.own_title = own_title

    @property
    def available(self):
        return bool(shutil.which("wmctrl"))

    @staticmethod
    def _run(arguments):
        try:
            return subprocess.run(
                arguments,
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return None

    def list_windows(self):
        if not self.available:
            return []
        result = self._run(["wmctrl", "-lx"])
        if not result or result.returncode != 0:
            return []

        windows = []
        for line in result.stdout.splitlines():
            window = parse_wmctrl_line(line)
            if not window or window.desktop < 0:
                continue
            if self.own_title.lower() in window.title.lower():
                continue
            windows.append(window)
        return windows

    def active_window_id(self):
        result = self._run(["xprop", "-root", "_NET_ACTIVE_WINDOW"])
        if not result or result.returncode != 0:
            return None
        match = re.search(r"0x[0-9a-fA-F]+", result.stdout)
        return match.group(0).lower() if match else None

    def is_vdi_active(self):
        active = self.active_window_id()
        if not active:
            return False
        for window in self.list_windows():
            if int(window.window_id, 16) == int(active, 16):
                return window.is_vdi
        return False

    def preferred_vdi(self):
        windows = self.list_windows()
        active = self.active_window_id()
        if active:
            for window in windows:
                if int(window.window_id, 16) == int(active, 16) and window.is_vdi:
                    return window
        return next((window for window in windows if window.is_vdi), None)

    def activate(self, window_id):
        result = self._run(["wmctrl", "-ia", window_id])
        return bool(result and result.returncode == 0)

    def apply_overlay_hints(self, tk_window_id):
        """Ask an EWMH-compatible X11 window manager to keep the dock above apps."""
        if not self.available:
            return False
        window_id = hex(int(tk_window_id))
        # wmctrl accepts at most two state properties in each request.
        results = [self._run(["wmctrl", "-i", "-r", window_id, "-b", states])
                   for states in ("add,above,sticky", "add,skip_taskbar,skip_pager")]
        return all(result and result.returncode == 0 for result in results)
