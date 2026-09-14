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
| Windows | `TopDock-Windows-v5.zip` | Windows x64; Python/.NET installation not needed |
| Linux portable | [TopDock-Linux-x86_64](https://github.com/okskaok3-hub/TopDock/releases/download/v1.1.0/TopDock-Linux-x86_64) | x86-64, glibc 2.31+, X11 desktop; Python/Tk and helpers bundled |
| Other Linux architectures | Build from source | Python 3, Tk, X11 and the system tools listed below |

The first repository release is **v1.0.0**. The package suffixes `v5` and `v4`
retain the original platform-specific build numbers. See [CHANGELOG.md](CHANGELOG.md)
for how the Windows and Linux versions developed.

## Features

- Top-edge auto-hide and `Ctrl+Alt+Space` reveal.
- Application-name cards, dedicated card row, and slim horizontal slider.
- **PASTE:** type the host clipboard into a supported VDI client.
- **SHOT:** drag any desktop region and copy its image to the host clipboard.
- Lossless screenshots at original pixel dimensions; a 4K selection stays 4K.
- **AUTO / AREA:** toggle the built-in auto-clicker and select its click area.
- **START / PIN:** enable login startup or keep the dock visible.
- Settings and creator credit.

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

1. Download and extract `TopDock-Windows-v5.zip` from Releases.
2. Run `TopDock.exe` from the extracted folder.
3. Move the pointer to the top edge or press `Ctrl+Alt+Space`.
4. Use START or Settings to enable Windows startup if wanted.

The executable includes the .NET runtime and native WPF libraries. Only one
Windows TopDock instance runs at a time. Exit the old instance from the tray
before replacing its executable.

Build with the .NET 10 SDK on Windows:

```powershell
dotnet publish windows-topdock/TopDock.csproj -c Release -o release/windows
release/windows/TopDock.exe --content-test
```

See [Windows guide](docs/WINDOWS.md).

## Linux quick start

Download the single `TopDock-Linux-x86_64` executable from Releases. No installer
or `.sh` launcher is required:

```bash
chmod +x TopDock-Linux-x86_64
./TopDock-Linux-x86_64
```

Run as your normal desktop user in an X11 session. SSH alone does not create a
visible desktop connection. This portable binary targets glibc 2.31+ x86-64
desktops, not ARM, Alpine/musl, or native Wayland. It extracts bundled files to
a temporary directory at launch; that location must allow execution.
The older Kali-specific package remains available in release v1.0.0.

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
| Reveal | Top 14px or Ctrl+Alt+Space | Top edge or Ctrl+Alt+Space |
| Switch | Click card; Alt+1…9 while focused | Click card; Alt+1…9 while focused |
| Browse overflow | Slider or wheel | Slider or wheel; arrow keys on slider |
| Search windows | Search button / Ctrl+F | Not implemented |
| Close another window | Middle-click card | Not implemented |
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
