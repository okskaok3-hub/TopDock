# TopDock

A compact desktop dock for switching applications, typing host clipboard text
into VDI sessions, selecting screenshot regions, and controlling an integrated
auto-clicker.

**Made with love by Aditya Rathee.**

TopDock has a native **Windows WPF** edition and a **Linux X11/Tk** edition.
Both reveal at the top edge, show application names instead of document titles,
and provide a horizontal slider for reaching windows that do not fit on screen.

## Downloads

Open [Releases](https://github.com/okskaok3-hub/TopDock/releases) for the current executable packages.

| Edition | Current package | Requirements |
| --- | --- | --- |
| Windows portable | [TopDock-Windows-v1.4.1.zip](https://github.com/okskaok3-hub/TopDock/releases/download/v1.4.1/TopDock-Windows-v1.4.1.zip) | Windows x64; includes TopDock and Zoom Clipboard dashboard |
| Linux portable | [TopDock-Linux-Ubuntu24-x64.tar.gz](https://github.com/okskaok3-hub/TopDock/releases/download/v1.4.0/TopDock-Linux-Ubuntu24-x64.tar.gz) | Ubuntu 24.04 x64, X11. Includes the TopDock binary and Zoom Clipboard |
| Other Linux architectures | Build from source | Python 3, Tk, X11 and the system tools listed below |

**[Linux v1.4.0](https://github.com/okskaok3-hub/TopDock/releases/tag/v1.4.0)** brings the
Windows dock styling to X11, including rounded controls, application icons, a
magenta active-window marker, and a high-contrast screenshot cursor. Startup
and Zoom Clipboard are in Settings. Search is hidden by default, click areas
reset on restart, and the top edge waits 0.75 seconds before revealing the dock.

The [v1.3.0 Linux binary](https://github.com/okskaok3-hub/TopDock/releases/download/v1.3.0/TopDock-Linux-x86_64)
is available for the older glibc 2.31 baseline.

The first repository release is **v1.0.0**. The package suffixes `v5` and `v4`
retain the original platform-specific build numbers. See [CHANGELOG.md](CHANGELOG.md)
for how the Windows and Linux versions developed.

## Features

- Top-edge auto-hide and `Ctrl+Alt+Space` reveal.
- Application-name cards, dedicated card row, and slim horizontal slider.
- **PASTE:** type the host clipboard into a supported VDI client.
- **SHOT:** drag any desktop region and copy its image to the host clipboard.
- Lossless screenshots at original pixel dimensions; a 4K selection stays 4K.
- **AUTO:** toggle the built-in auto-clicker; choose its area in Settings.
- Draggable dock and a Settings action that collapses it into a movable circle.
- Drag quick buttons into your preferred order, or hide them in Settings.
- **Open Zoom Clipboard:** launch the companion dashboard from Linux Settings. Windows packages include the native dashboard.
- Search, Pin, Startup, clipboard preview and version information in Settings.

### Text fidelity

Paste preserves printable ASCII, tabs, and line breaks. It normalizes Windows
line endings and clears editor-generated indentation after a new line. Modifier
release handling reduces stuck Shift/capitalization issues in remote clients.

**Non-ASCII symbols and letters are skipped and counted**, including arrows,
emoji, accented characters and non-Latin scripts. For example, `A→B` becomes `AB`.
This is a VDI compatibility fallback, not lossless Unicode paste. The original
host clipboard is not modified. Review pasted code when the completion message
reports skipped characters. The Python engine can optionally trim trailing
whitespace using its shared configuration.

### Screenshot quality

SHOT captures the selected physical pixels without resampling or JPEG encoding.
Linux publishes PNG; Windows publishes PNG and a standard bitmap format.
A 3840×2160 region remains 3840×2160, while a smaller region stays its original
size. There is no invented detail or forced upscaling. A destination app may
resize or recompress the image after pasting.

The dock hides during capture. Drag to select; Escape or right-click cancels.
Windows selection spans the virtual desktop, including multiple monitors.

## Windows quick start

1. Download and extract `TopDock-Windows-v1.4.1.zip` to a permanent folder.
2. Run `TopDock.exe`; keep `ZoomClipboardUI.exe` beside it.
3. Hold the pointer at the top edge for 0.75 seconds or press `Ctrl+Alt+Space`.
4. Open **Settings** to enable startup, launch Zoom Clipboard, show search, or change the reveal mode.

The executables include their .NET runtimes and native libraries. Only one
Windows TopDock instance runs at a time. Exit the old instance from the tray
before replacing its executable.

To build Windows v1.4.1 from source, check out tag `v1.4.1` and use the .NET 10 SDK:

```powershell
dotnet publish windows-topdock/TopDock.csproj -c Release -o release/windows
release/windows/TopDock.exe --content-test
```

See the [Windows v1.4.1 guide](https://github.com/okskaok3-hub/TopDock/blob/v1.4.1/docs/WINDOWS.md).

## Linux quick start

Download the Linux archive above, extract it, and run the binary in an X11 desktop session.

```bash
tar -xzf TopDock-Linux-Ubuntu24-x64.tar.gz
./TopDock-Linux-x86_64 --check
./TopDock-Linux-x86_64
```

Keep the `zoom-clipboard` directory beside the binary. The companion opens in
your browser and uses the system Python 3. TopDock extracts its bundled runtime
to a temporary directory at launch and requires execution permission there.

Source installation on Debian/Ubuntu/Kali:

```bash
sudo apt install python3 python3-venv python3-tk wmctrl x11-utils xclip scrot
chmod +x install-linux.sh run-linux.sh build-linux.sh
./install-linux.sh
~/.local/bin/topdock-vdi
```

Build an executable locally:

```bash
./build-linux.sh
./dist-linux/TopDock-VDI
```

See [Linux guide](LINUX.md) and [build and testing guide](docs/BUILDING.md).

## Controls and platform differences

| Action | Windows | Linux |
| --- | --- | --- |
| Reveal | Hold at the top edge for 0.75 seconds by default, or Ctrl+Alt+Space | Hold at the top edge for 0.75 seconds by default, or Ctrl+Alt+Space |
| Switch | Click card; Alt+1…9 while focused | Click card; Alt+1…9 while focused |
| Browse overflow | Slider or wheel | Slider or wheel; arrow keys on slider |
| Search windows | Enable in Settings, then use the search button or Ctrl+F | Enable in Settings, then use the search button or Ctrl+F |
| Close another window | Middle-click card | Middle-click card |
| Capture | SHOT; full virtual desktop selector | SHOT; X11 desktop selector |
| VDI detection | Citrix / Remote Desktop | Citrix / Remmina / FreeRDP / Horizon |

## Documentation

- [Changelog and historical improvements](CHANGELOG.md)
- [Windows installation and controls](docs/WINDOWS.md)
- [Linux installation and requirements](LINUX.md)
- [Building and validation](docs/BUILDING.md)
- [Troubleshooting and known limitations](docs/TROUBLESHOOTING.md)
- [Source map](CODEMAP.md)
- [Original VDI Toolkit manual](MANUAL.md)

The original Python control center is also included (`main.py`). Its optional
AI Screenshot feature is separate from TopDock SHOT: when explicitly used, it
sends an image/prompt to the configured AI provider. TopDock's ordinary SHOT
button copies locally to the clipboard.

## Development

Release binaries are attached to GitHub Releases rather than committed to Git.
The repository contains source and tests; local credentials, configuration,
captured screens, virtual environments and generated build files are excluded.
When reporting an issue, include OS/session type, package version, display
scaling, VDI client, reproduction steps, and any error text.
