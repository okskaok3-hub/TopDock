# VDI Toolkit - Platform Utilities
# Cross-platform support for Windows and Linux

import os
import sys
import platform
import shutil
from pathlib import Path

# Detect platform
IS_WINDOWS = sys.platform == 'win32'
IS_LINUX = sys.platform.startswith('linux')
IS_MAC = sys.platform == 'darwin'
PLATFORM = platform.system()


def get_config_dir():
    """Get platform-specific config directory."""
    if IS_WINDOWS:
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif IS_LINUX:
        base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    elif IS_MAC:
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.path.expanduser('~')

    return Path(base) / 'VDIToolkit'


def get_autostart_dir():
    """Get platform-specific autostart directory."""
    if IS_LINUX:
        return Path(os.path.expanduser('~/.config/autostart'))
    return None


def get_exe_path():
    """Get path to current executable."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def get_launch_args():
    """Return the executable and arguments needed to relaunch this app."""
    if getattr(sys, 'frozen', False):
        return [sys.executable]
    return [sys.executable, str(Path(sys.argv[0]).resolve())]


def _desktop_exec_quote(value):
    """Quote one freedesktop Exec argument without invoking a shell."""
    escaped = str(value).replace('\\', '\\\\').replace('"', '\\"')
    escaped = escaped.replace('`', '\\`').replace('$', '\\$')
    return f'"{escaped}"'


def get_desktop_exec():
    return " ".join(_desktop_exec_quote(value) for value in get_launch_args())


def get_autostart_file():
    launch_text = " ".join(get_launch_args()).lower()
    filename = "topdock-vdi.desktop" if "topdock" in launch_text else "vdi-toolkit.desktop"
    return get_autostart_dir() / filename


def is_in_startup():
    """Check if app is configured to start with OS."""
    if IS_WINDOWS:
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "VDIToolkit")
                winreg.CloseKey(key)
                return True
            except:
                winreg.CloseKey(key)
                return False
        except:
            return False

    elif IS_LINUX:
        return get_autostart_file().exists()

    return False


def toggle_startup():
    """Toggle autostart on/off."""
    if IS_WINDOWS:
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

            if is_in_startup():
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
                winreg.DeleteValue(key, "VDIToolkit")
                winreg.CloseKey(key)
            else:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
                winreg.SetValueEx(key, "VDIToolkit", 0, winreg.REG_SZ, f'"{get_exe_path()}"')
                winreg.CloseKey(key)
            return is_in_startup()
        except Exception as e:
            print(f"Startup toggle error: {e}")
            return is_in_startup()

    elif IS_LINUX:
        autostart_dir = get_autostart_dir()
        desktop_file = get_autostart_file()
        is_topdock = desktop_file.name == "topdock-vdi.desktop"

        try:
            if is_in_startup():
                desktop_file.unlink()
            else:
                autostart_dir.mkdir(parents=True, exist_ok=True)
                desktop_content = f"""[Desktop Entry]
Type=Application
Name={"TopDock VDI" if is_topdock else "VDI Toolkit"}
Comment={"Floating application switcher and VDI tools" if is_topdock else "VDI Clipboard and Automation Tools"}
Exec={get_desktop_exec()}
Icon=vdi-toolkit
Terminal=false
Categories=Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""
                desktop_file.write_text(desktop_content, encoding="utf-8")
                desktop_file.chmod(0o755)
            return is_in_startup()
        except Exception as e:
            print(f"Startup toggle error: {e}")
            return is_in_startup()

    return False


def requires_root_for_keyboard():
    """The Linux pynput backend does not require root in a normal X11 session."""
    return False


def get_linux_session_type():
    if not IS_LINUX:
        return ""
    return os.environ.get("XDG_SESSION_TYPE", "").strip().lower()


def get_linux_runtime_warnings():
    """Return actionable Linux desktop compatibility warnings."""
    if not IS_LINUX:
        return []

    warnings = []
    session_type = get_linux_session_type()
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        warnings.append("No graphical display was detected. Start TopDock inside your desktop session.")
    if session_type == "wayland":
        warnings.append(
            "Wayland may block global hotkeys, window switching, and overlays. "
            "Use an X11/Xorg login session for full TopDock functionality."
        )
    if not shutil.which("wmctrl"):
        warnings.append("wmctrl is not installed; active-window cards will be unavailable.")
    if not shutil.which("scrot"):
        warnings.append("scrot is not installed; region screenshots may be unavailable.")
    if not shutil.which("xclip"):
        warnings.append("xclip is not installed; image clipboard output will be unavailable.")
    return warnings


def print_linux_keyboard_warning():
    """Print Linux session limitations without recommending unsafe GUI sudo."""
    for warning in get_linux_runtime_warnings():
        print(f"[WARNING] {warning}")
