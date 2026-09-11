# Building and testing

## Windows

Requirements: Windows x64 and .NET 10 SDK.

```powershell
dotnet build windows-topdock/TopDock.csproj -c Release
dotnet publish windows-topdock/TopDock.csproj -c Release -o release/windows
release/windows/TopDock.exe --content-test
```

The project enables self-contained, single-file publishing and native library
extraction. Distributing an EXE without the WPF native libraries caused an early
startup crash; keep `IncludeNativeLibrariesForSelfExtract` enabled.

## Linux

Install the packages in LINUX.md. For desktop tests also install `xvfb` and `xauth`.
Use `build-linux.sh` to create an isolated environment and a PyInstaller ELF.

```bash
chmod +x build-linux.sh
./build-linux.sh
.venv-linux-build/bin/python -m unittest discover -s tests -p 'test_linux_*.py' -v
.venv-linux-build/bin/python -m unittest discover -s tests -p test_paste_text.py -v
.venv-linux-build/bin/python -m unittest discover -s tests -p test_clipboard_paste.py -v
.venv-linux-build/bin/python -m unittest discover -s tests -p test_settings.py -v
xvfb-run -a -s '-screen 0 3840x2160x24' env XDG_SESSION_TYPE=x11 \
  .venv-linux-build/bin/python tests/linux_desktop_smoke.py
xvfb-run -a env XDG_SESSION_TYPE=x11 \
  .venv-linux-build/bin/python tests/linux_binary_smoke.py
```

Desktop tests use an isolated X display and its clipboard. They check card sizing,
slider reach, auto-hide position, Settings credit, PNG pixel/dimension fidelity,
real capture, and 4K clipboard readback. The binary test verifies the packaged
app stays running and creates its X11 window. These do not prove compatibility
with every compositor, multi-monitor setup or VDI client.

The release binary was built on Kali 2026.2 with Python 3.13.12, PyInstaller 6.18.0
and glibc 2.42. Build on your oldest supported distribution when distributing to
older systems. Python dependencies are currently minimum-version requirements,
not a fully locked reproducible build environment.

## Source structure

- `windows-topdock/`: native WPF application and input/capture helpers.
- `linux_topdock.py`: Tk dock, layout, selection UI, main-thread dispatch.
- `linux_window_service.py`: X11 application discovery and activation.
- `linux_screenshot_service.py`: original-pixel PNG and X11 clipboard output.
- `paste_text.py`: Unicode skip policy shared by Python consumers.
- `clipboard_paste.py`: cancellable/pauseable keyboard typing engine.
- `auto_clicker.py`: click-area selection and VDI-scoped automation.
- `tests/`: unit tests and isolated Linux desktop/binary smoke tests.
- `main.py`, `ui_app.py`: original Python Toolkit control center.

## Release packaging

Commit source and documentation only. Publish executable archives as Release
assets and include SHA-256 checksums. Build Windows on Windows and Linux on
Linux. A `.zip` source archive is not a Linux executable.
