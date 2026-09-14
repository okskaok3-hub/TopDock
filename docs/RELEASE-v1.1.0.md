# TopDock v1.1.0 — Windows & Linux Portable

One release with ready-to-run desktop builds for both platforms. No installer,
Python setup, or separate .NET installation is needed.

## Downloads

| Platform | Download | Requirements |
| --- | --- | --- |
| Windows | [Windows portable ZIP](https://github.com/okskaok3-hub/TopDock/releases/download/v1.1.0/TopDock-Windows-v5.zip) | Windows x64 |
| Linux | [Linux portable executable](https://github.com/okskaok3-hub/TopDock/releases/download/v1.1.0/TopDock-Linux-x86_64) | x86-64, glibc 2.31+, X11 desktop |
| Verification | [SHA-256 checksums](https://github.com/okskaok3-hub/TopDock/releases/download/v1.1.0/SHA256SUMS-v1.1.0.txt) | Checksums for both downloads |

Choose a download above, not GitHub's automatically generated **Source code**
archives. Those contain source, not the ready-to-run app.

## Windows quick start

1. Download and extract `TopDock-Windows-v5.zip` to a permanent folder.
2. Open the extracted folder and run `TopDock.exe`.
3. Move the pointer to the top edge or press `Ctrl+Alt+Space`.
4. Enable START in the dock if you want login startup.

Exit an existing instance from the tray before updating. The ZIP contains the
self-contained executable and its README. Windows remains the existing v5
build, unchanged from v1.0.0; it is included here for a single download page.
Preferences remain in your user profile, so portable means no installation,
not that all settings travel with the executable.

## Linux quick start

Download `TopDock-Linux-x86_64`, then run these commands in its folder:

```bash
chmod +x TopDock-Linux-x86_64
./TopDock-Linux-x86_64
```

This is a real single-file ELF executable, not a shell launcher. Python, Tk,
wmctrl, xprop, xclip, scrot and the PNG codec are bundled. Run as your normal
desktop user, not with sudo. An executable temporary directory is needed for
runtime extraction. No `.sh` installer is required.

## Included features

- Auto-hiding top dock with application-name cards and overflow slider.
- Host clipboard typing into supported VDI clients.
- Integrated auto-clicker with ON/OFF and region selection.
- Crosshair screenshot selection and original-resolution clipboard images.
- Login startup, pin controls, Settings and creator credit.

## Improvements and validation

Linux portability now targets glibc 2.31 instead of the previous Kali-specific
2.42 baseline. Bundled helper discovery and PNG codec packaging remove the
need to install those desktop utilities separately.

Linux startup/window creation was checked on Ubuntu 20.04. Original 3840×2160
PNG clipboard capture passed on Ubuntu 20.04, clean Ubuntu 22.04 and Kali using
isolated X11 displays. These are not tests of every desktop or VDI client.
The Windows download matches the previously published v5 asset byte for byte.

## Known limitations

- Linux requires X11 and x86-64/glibc: ARM, Alpine/musl and native Wayland are
  not supported by this binary.
- VDI typing skips and reports non-ASCII characters, including arrows and emoji.
  Review pasted code if characters were skipped.
- Screenshot output preserves captured pixels; it does not upscale a small
  selection to invented 4K detail.
- Secure or exclusive desktop surfaces may block overlays, typing or capture.

See the [full changelog](https://github.com/okskaok3-hub/TopDock/blob/main/CHANGELOG.md),
[Windows guide](https://github.com/okskaok3-hub/TopDock/blob/main/docs/WINDOWS.md),
and [Linux guide](https://github.com/okskaok3-hub/TopDock/blob/main/LINUX.md).

Made with love by Aditya Rathee.
