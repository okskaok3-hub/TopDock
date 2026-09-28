# TopDock v1.2.0 — Windows & Linux Portable

Download the executable for your platform:

| Platform | Asset | Requirements |
| --- | --- | --- |
| Windows | [TopDock-Windows-x64.exe](https://github.com/okskaok3-hub/TopDock/releases/download/v1.2.0/TopDock-Windows-x64.exe) | Windows x64 |
| Linux | [TopDock-Linux-x86_64](https://github.com/okskaok3-hub/TopDock/releases/download/v1.2.0/TopDock-Linux-x86_64) | x86-64, glibc 2.31+, X11 desktop |

These are direct executables. The Windows build includes .NET; the Linux build
bundles Python, Tk and its desktop helpers. No installer or shell launcher is
needed. Download the asset above instead of GitHub's source archives.

On Windows, save the EXE in a permanent folder, exit any older TopDock instance
from the tray, then run the new EXE. On Linux:

```bash
chmod +x TopDock-Linux-x86_64
./TopDock-Linux-x86_64
```

## Changes

- Drag the dock by its logo; collapse it into a movable circular overlay from
  Settings and restore it by clicking the circle.
- Use one AUTO button to toggle the clicker. Click it once to choose an area if
  no area is saved; choose a new area from Settings later.
- Preview clipboard text or an image with + and − zoom controls using CLIP.
- Find Search, Pin and Startup in Settings along with the version number.
- Linux Settings now supports searching application cards by name.

## Validation and limits

- Windows x64 build passed the content test for ASCII paste behavior and a
  pixel-exact 3840×2160 PNG roundtrip.
- Linux source passed X11 layout, clipboard preview, search, circle and 4K
  screenshot checks on an isolated display. The packaged executable passed
  startup and 4K clipboard checks on Ubuntu 20.04 and clean Ubuntu 22.04.
- Linux requires an X11/glibc desktop; ARM, Alpine/musl and native Wayland are
  outside the current binary target.
- Non-ASCII VDI paste characters, including arrows and emoji, are skipped and
  reported. Secure or exclusive desktops can block overlays or capture.

See [README](https://github.com/okskaok3-hub/TopDock/blob/main/README.md),
[changelog](https://github.com/okskaok3-hub/TopDock/blob/main/CHANGELOG.md),
and the [SHA-256 checksum file](https://github.com/okskaok3-hub/TopDock/releases/download/v1.2.0/SHA256SUMS.txt).

Made with love by Aditya Rathee.
