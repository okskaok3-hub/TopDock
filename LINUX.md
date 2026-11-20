# TopDock VDI for Linux

TopDock VDI is a compact, auto-hiding Linux dock for switching applications and
using local clipboard typing inside authorized Citrix, Remmina, FreeRDP, or
VMware Horizon sessions.

## Supported desktop environment

The [v1.4.0 Linux archive](https://github.com/okskaok3-hub/TopDock/releases/download/v1.4.0/TopDock-Linux-Ubuntu24-x64.tar.gz)
was built for **Ubuntu 24.04 x64 on X11**. TopDock bundles Python, Tk, wmctrl,
xprop, xclip, scrot, and the PNG capture codec. The included Zoom Clipboard
companion uses your system Python 3 and opens in a browser.

```bash
tar -xzf TopDock-Linux-Ubuntu24-x64.tar.gz
./TopDock-Linux-x86_64 --check
./TopDock-Linux-x86_64
```

Keep the `zoom-clipboard` directory next to the executable. The
[v1.3.0 Linux binary](https://github.com/okskaok3-hub/TopDock/releases/download/v1.3.0/TopDock-Linux-x86_64)
is available for systems on the older glibc 2.31 baseline.

Use an X11/Xorg desktop session for complete functionality. GNOME, KDE Plasma,
Xfce, Cinnamon, and MATE are supported when they run on X11.

Wayland intentionally restricts global keyboard injection, window enumeration,
and always-on-top overlays. TopDock detects Wayland and shows a warning. An
XWayland session may provide partial functionality, but an Xorg login session is
recommended for VDI paste and full-screen reveal.

## Install on Ubuntu or Debian

```bash
sudo apt update
sudo apt install python3 python3-venv python3-tk wmctrl x11-utils xclip scrot
chmod +x install-linux.sh run-linux.sh build-linux.sh
./install-linux.sh
topdock-vdi
```

Validate the installation without opening the dock:

```bash
topdock-vdi --check
```

For Fedora:

```bash
sudo dnf install python3 python3-tkinter wmctrl xprop xclip scrot
chmod +x install-linux.sh run-linux.sh build-linux.sh
./install-linux.sh
```

Run TopDock as your normal desktop user. Do not run the graphical application
with `sudo`; that can disconnect it from your clipboard and display session.

## Controls

- Drag the logo to move the dock. In Settings, collapse it to a circular icon;
  drag the icon to move it and click to restore the dock.
- **Settings → Preview local clipboard** opens host clipboard text or PNG images.
- Drag quick buttons to reorder them; Settings can hide/show each button.
- Quick-button order, visibility and dock position persist across restarts.
- **Settings → Open Zoom Clipboard** launches the included Linux dashboard. Source builds can use the companion installed from the [Zoom Clipboard repository](https://github.com/okskaok3-hub/zoom-clipboard).
- **Start TopDock with Linux**, **Compact window cards**, and **Show window search** are in Settings. Search is hidden by default. When enabled, use its dock button or **Ctrl+F** while TopDock is focused.
- Middle-click an application card to request that the window close.
- Hold the pointer at the top edge for 0.75 seconds to reveal TopDock, or press `Ctrl+Alt+Space`.
- In **Settings → Open at top edge**, choose **After 0.75 seconds**, **Immediately**, or **Shortcut only**. Shortcut-only mode requires a working global hotkey. Turn off **Keep dock open** to let the dock hide when you move away.
- Select an application card to switch windows. Cards show application names,
  not full document titles. Drag the slim horizontal slider below the cards (or
  use the mouse wheel over them) to reach every open application.
- Select **SHOT**, then use the crosshair to drag any area of the full desktop.
  The high-contrast yellow crosshair marks the selection point, and the selected region is copied to the Linux host clipboard as a PNG image.
  Press `Escape` to cancel without capturing.
- Select **PASTE** to capture the Linux host clipboard, focus an open VDI client,
  and type the text as keyboard input.
  Unsupported non-ASCII symbols (including arrows, emoji, and non-Latin letters)
  are skipped and counted in the completion message. The remaining ASCII code,
  tabs, and line breaks are preserved; the host clipboard itself is unchanged.
  For example, `A→B` becomes `AB`, not `A->B`.
- Screenshots use original-resolution, lossless PNG without enlargement or
  downscaling. A full 3840×2160 selection on a 4K desktop stays 3840×2160.
  Smaller selections remain their original size.
- Select **AUTO** and drag an area on your first use after each launch. Choose
  **Start auto clicker**, **Stop auto clicker**, or **Select click area** from the
  **AUTO** menu. Clicking only runs while Citrix, Remmina, FreeRDP, or VMware
  Horizon is active.
- Use **Settings** to enable login startup or keep the dock open.
- Cards occupy a fixed 44-pixel row, with a separate subtle slider underneath.

## Build a standalone Linux executable

PyInstaller must run on Linux; it cannot produce a Linux executable from
Windows. On the Linux target machine run:

```bash
./build-linux.sh
./dist-linux/TopDock-VDI
```

## Troubleshooting

- **No application cards:** install `wmctrl` and `xprop`, then restart TopDock.
- **Clipboard unavailable:** install `xclip` or `xsel` and copy the text again.
- **Screenshot does not capture:** install `scrot`. If it captures but does not
  copy, install `xclip`; PNG clipboard output uses its `image/png` target.
- **Hotkeys or typing blocked:** log out and choose an Xorg/X11 session.
- **Dock hidden by exclusive full screen:** use the VDI client's borderless or
  maximized mode. X11 compositors can keep TopDock above normal full-screen
  windows, but secure screens and exclusive compositor surfaces can cover it.
- **Missing characters:** select Safe or Ultra-Safe timing in the original VDI
  Toolkit control center, which shares the same configuration file.

Configuration is stored in `~/.config/VDIToolkit/config.json` by default.
TopDock remembers your dock preferences. The autoclick area lasts for the current run.
