# TopDock VDI for Linux

TopDock VDI is a compact, auto-hiding Linux dock for switching applications and
using local clipboard typing inside authorized Citrix, Remmina, FreeRDP, or
VMware Horizon sessions.

## Supported desktop environment

The included `TopDock-VDI` binary is built for **x86-64 Kali Linux 2026.2
(glibc 2.42 or newer)**. It bundles Python and Tk. Older distributions should
build from source on their own system using `build-linux.sh`.

To run the binary in an X11 desktop session:

```bash
sudo apt install wmctrl x11-utils xclip scrot
chmod +x TopDock-VDI
./TopDock-VDI --check
./TopDock-VDI
```

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

- Move the pointer to the top edge or press `Ctrl+Alt+Space` to reveal TopDock.
- Select an application card to switch windows. Cards show application names,
  not full document titles. Drag the slim horizontal slider below the cards (or
  use the mouse wheel over them) to reach every open application.
- Select **SHOT**, then use the crosshair to drag any area of the full desktop.
  The selected region is copied to the Linux host clipboard as a PNG image.
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
- Select **AREA** and drag a rectangle to configure the auto-clicker.
- Select **AUTO** to toggle clicking. TopDock pauses clicks whenever the active
  window is not Citrix, Remmina, FreeRDP, or VMware Horizon.
- Select **START** to enable or disable login startup.
- Select **PIN** to keep the dock open.
- Select **SETTINGS** for controls, Exit, and “Made with love by Aditya Rathee”.
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
The selected auto-click area is saved there and restored at the next launch.
