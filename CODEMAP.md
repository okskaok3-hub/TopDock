# VDI Toolkit Code Map

This repository contains a Python/Tkinter control center and a premium Linux
TopDock for authorized VDI input automation.

## Runtime flow

`main.py`
- Creates the hidden Tk root and starts the main event loop.
- Instantiates the paste engine, auto-clicker, AI assistant, notifications, UI,
  and system tray.
- Uses a thread-safe status queue so worker and tray threads never update Tk
  directly.

`linux_topdock.py`
- Provides the auto-hiding three-section Linux dock.
- Shows every active X11 application in a horizontally scrollable card strip,
  using application names only.
- Integrates host clipboard typing, VDI-scoped auto-clicking, area selection,
  region screenshots, pinning, and Linux login startup.

`linux_screenshot_service.py`
- Captures a selected desktop region through PyAutoGUI.
- Encodes it as PNG and publishes `image/png` to the X11 clipboard with `xclip`.

`linux_window_service.py`
- Enumerates and activates X11 windows through `wmctrl`.
- Recognizes Citrix, Remmina, FreeRDP, and VMware Horizon sessions.
- Applies EWMH always-on-top hints for full-screen VDI compatibility.

`clipboard_paste.py`
- Reads clipboard text and types it character-by-character for VDI use.
- Supports paste, pause/resume, and cancel hotkeys.
- Uses a lock and events to prevent duplicate workers and stop cleanly.
- Reports progress and unsupported-character errors instead of silently dropping
  input.

`auto_clicker.py`
- Provides fullscreen area selection and randomized clicking.
- Dispatches global hotkey callbacks to Tk's main thread.

`notification.py`
- Provides stacked Tk notification cards.

`tray_menu.py`
- Provides the cross-platform system tray menu.
- Marshals actions that touch Tk or runtime state onto the UI thread.

`ui_app.py`
- Provides the Tk control center.
- Exposes paste mode, timing, trimming, pause/resume, cancel, and hotkey
  controls.

`settings.py`
- Validates and persists JSON configuration.
- Uses atomic config writes and rolls back in-memory changes when persistence
  fails.

`platform_utils.py`
- Provides platform-specific config, startup, and permission helpers.
- Creates correctly quoted freedesktop autostart entries on Linux.

`startup_diagnostics.py`
- Checks dependencies and reports Tk/keyboard startup problems.

## Tests

The `tests/` directory covers configuration validation, paste lifecycle and
character emission, diagnostics, auto-clicker helpers, and AI payload helpers.

## Build artifacts

`build/`, `build-*`, `dist/`, `dist-*`, `__pycache__/`, and `.tmp-tests/` are
generated content and should not be treated as source files.

## Linux entry points

- `run-linux.sh` creates an isolated environment and starts TopDock.
- `install-linux.sh` installs a user launcher and application-menu entry.
- `build-linux.sh` creates a Linux PyInstaller executable when run on Linux.
- `LINUX.md` documents installation and X11/Wayland compatibility.
- `requirements-topdock-linux.txt` contains only the dock's runtime packages;
  `requirements-linux.txt` remains available for the complete control center.

## Windows TopDock

- `windows-topdock/MainWindow.xaml` defines the premium dock, visible window
  slider, SHOT control, and Settings credit.
- `windows-topdock/ScreenCaptureSelectionWindow.*` provides the crosshair region
  selector across the complete Windows virtual desktop.
- `windows-topdock/ScreenshotService.cs` captures physical pixels and publishes
  the resulting image to the Windows clipboard.
