# Windows TopDock

## Install and update

Download and extract `TopDock-Windows-v1.3.0.zip` into a permanent folder, then
run `TopDock.exe`. Keep `ZoomClipboardUI.exe` beside it. No installer or separate
.NET runtime is required.
Use Settings to register login startup. If you move the executable,
relaunch TopDock after moving it so the startup entry points to the new location.

To update, exit TopDock from the notification-area menu, replace the extracted
files, and launch the new executable. The single-instance guard prevents running
two copies simultaneously.

## Controls

- Top 18 pixels of any monitor / Ctrl+Alt+Space: reveal or toggle the dock,
  including after dragging it or collapsing it to a circle.
- Application card: switch; middle-click: request close.
- Slider / mouse wheel: browse all open windows.
- Alt+1 through Alt+9: switch while TopDock has focus.
- Search / Ctrl+F: search application names or window titles.
- PASTE: capture local clipboard text, focus Citrix/Remote Desktop, then type.
- SHOT: drag a rectangle anywhere on the virtual desktop. Escape/right-click
  cancels. Copy original pixels as PNG and bitmap.
- AUTO: click to toggle; its area is selected in Settings.
- ZOOM: launch the bundled Zoom Clipboard dashboard; a different executable
  can be selected in Settings. The local text/image preview is also in Settings.
- Drag quick buttons to reorder them; Settings can hide or show each one.
- Drag the logo to move the dock. Settings can collapse it to a draggable circle.
- Settings: search, Pin, login Startup, version number, and Exit.

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
3840×2160 PNG roundtrip and top-edge activation without injecting keys or replacing the clipboard.

Final manual checks should use the interactive Windows desktop: reveal at the
top edge, drag the slider, switch applications, open Settings, capture a region,
and paste its image into an image editor. Check VDI typing with a disposable
document before using a production editor.
