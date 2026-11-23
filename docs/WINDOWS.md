# Windows TopDock

## Install and update

Download and extract `TopDock-Windows-v1.4.1.zip` into a permanent folder, then
run `TopDock.exe`. Keep `ZoomClipboardUI.exe` beside it. No installer or separate
.NET runtime is required.
Use Settings to register login startup. If you move the executable,
relaunch TopDock after moving it so the startup entry points to the new location.

To update, exit TopDock from the notification-area menu, replace the extracted
files, and launch the new executable. The single-instance guard prevents running
two copies simultaneously.

## Controls

- Hold the pointer at the top edge for 0.75 seconds or press **Ctrl+Alt+Space**.
  Use **Settings → Open at top edge** to choose immediate or shortcut-only reveal.
- Application card: switch; middle-click: request close.
- Slider / mouse wheel: browse all open windows.
- Alt+1 through Alt+9: switch while TopDock has focus.
- Search starts hidden. Enable **Show window search** in Settings to use the search button or **Ctrl+F**.
- PASTE: capture local clipboard text, focus Citrix/Remote Desktop, then type.
- **SHOT** uses a yellow crosshair with a dark outline. Drag a rectangle to copy the original pixels as PNG and bitmap. Press Escape or right-click to cancel.
- The first **AUTO** click after each restart opens the area selector. Use the **AUTO** menu to start, stop, or select a new area.
- **Settings → Open Zoom Clipboard** opens the bundled dashboard. Uploads accept `.txt`, `.csv`, `.log`, and `.md`. Files beginning with Windows MZ or Linux ELF executable signatures are rejected.
- Drag quick buttons to reorder them. Use the pin to keep TopDock open.

## Configuration

TopDock preferences: `%LOCALAPPDATA%\TopDock\settings.json`.
Shared typing delays: `%APPDATA%\VDIToolkit\config.json`.
Keep these files private; the optional Toolkit configuration can contain API keys.

## Validation

```powershell
dotnet publish windows-topdock/TopDock.csproj -c Release -o release/windows
release/windows/TopDock.exe --self-test
release/windows/TopDock.exe --paste-config-test
release/windows/TopDock.exe --content-test
```

`--self-test` enumerates windows. `--paste-config-test` reports timing settings.
`--content-test` validates skip behavior, ASCII preservation, and a pixel-exact
3840×2160 PNG roundtrip without injecting keys or replacing the clipboard.

Final manual checks should use the interactive Windows desktop: reveal at the
top edge, drag the slider, switch applications, open Settings, capture a region,
and paste its image into an image editor. Check VDI typing with a disposable
document before using a production editor.
