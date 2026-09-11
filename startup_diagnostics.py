# Startup diagnostics for the Python VDI Toolkit runtime.

import importlib

from platform_utils import IS_LINUX, print_linux_keyboard_warning

REQUIRED_MODULES = {
    "pyperclip": "pyperclip",
    "pyautogui": "pyautogui",
    "pynput": "pynput",
    "pystray": "pystray",
    "PIL": "Pillow",
}
if not IS_LINUX:
    REQUIRED_MODULES["keyboard"] = "keyboard"


def check_required_modules(required_modules=None, importer=None):
    """Return a list of missing dependency messages."""
    required_modules = required_modules or REQUIRED_MODULES
    importer = importer or importlib.import_module

    issues = []
    for module_name, package_name in required_modules.items():
        try:
            importer(module_name)
        except Exception as exc:
            issues.append(f"Missing dependency {package_name}: {exc}")
    return issues


def format_tk_error(exc):
    message = str(exc)
    if "init.tcl" in message:
        return (
            "Tkinter is installed without a usable Tcl/Tk runtime. "
            "Repair or reinstall Python with Tcl/Tk support."
        )
    return f"Tkinter failed to initialize: {message}"


def run_startup_checks():
    """Run lightweight diagnostics before importing the full app runtime."""
    print_linux_keyboard_warning()
    return check_required_modules()


def print_startup_report(issues):
    print("[ERROR] Startup checks failed:")
    for issue in issues:
        print(f"  - {issue}")
    print("\nInstall the missing dependencies or repair the Python environment, then try again.")


def create_hidden_root():
    """Create the Tk root window and return it, or raise a readable error."""
    import tkinter as tk

    try:
        root = tk.Tk()
    except Exception as exc:
        raise RuntimeError(format_tk_error(exc)) from exc

    root.withdraw()
    root.title("VDI Toolkit")
    return root
