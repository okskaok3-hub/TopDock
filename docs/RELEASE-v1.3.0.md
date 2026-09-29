# TopDock v1.3.0 — Windows & Linux

| Platform | Download | Requirements |
| --- | --- | --- |
| Windows | [TopDock-Windows-v1.3.0.zip](https://github.com/okskaok3-hub/TopDock/releases/download/v1.3.0/TopDock-Windows-v1.3.0.zip) | Windows x64 |
| Linux | [TopDock-Linux-x86_64](https://github.com/okskaok3-hub/TopDock/releases/download/v1.3.0/TopDock-Linux-x86_64) | x86-64, glibc 2.31+, X11 |

On Windows, extract the ZIP to a permanent folder, exit an older TopDock from
the tray, and run `TopDock.exe`. Keep `ZoomClipboardUI.exe` beside it. On Linux,
run `chmod +x TopDock-Linux-x86_64` and launch that binary from an X11 desktop.

## What's new

- Top-edge mouse reveal works after moving the dock and while it is collapsed
  to a circle. `Ctrl+Alt+Space` remains a recovery shortcut.
- Drag quick-action buttons to reorder them; show or hide each in Settings.
- AUTO remains one clicker control with area selection in Settings.
- ZOOM opens the bundled Windows Zoom Clipboard dashboard. Linux retains its
  local CLIP text/image preview; the Zoom dashboard is Windows-only.
- Dock position and quick-action preferences persist. Settings contains Pin,
  Search, Startup, clipboard preview on Windows, and version 1.3.0.

## Validation and limits

Windows content checks passed edge activation, ASCII paste and pixel-exact 4K
PNG encoding. Linux source passed X11 layout, quick-action persistence,
clipboard preview and 4K capture smoke tests; the portable ELF passed startup
and 4K readback in a clean Ubuntu 22.04 container. Real exclusive/full-screen
VDI overlays depend on the client and display mode. Unicode VDI paste still
skips unsupported symbols and reports the count. Zoom Clipboard sign-in, if
used, is initiated by the user in its own dashboard.

Verify downloads with [SHA256SUMS.txt](https://github.com/okskaok3-hub/TopDock/releases/download/v1.3.0/SHA256SUMS.txt).
