# Windows TopDock

## Install and update

Download `TopDock-Windows-v5.zip` from Releases and extract it to a permanent
folder. Run `TopDock.exe`. No installer or separate .NET runtime is required.
Use START or Settings to register login startup. If you move the executable,
disable and re-enable startup so it points to the new location.

To update, exit TopDock from the notification-area menu, replace the extracted
files, and launch the new executable. The single-instance guard prevents running
two copies simultaneously.

## Controls

- Top 14 pixels / Ctrl+Alt+Space: reveal or toggle the dock.
- Application card: switch; middle-click: request close.
- Slider / mouse wheel: browse all open windows.
- Alt+1 through Alt+9: switch while TopDock has focus.
- Search / Ctrl+F: search application names or window titles.
- PASTE: capture local clipboard text, focus Citrix/Remote Desktop, then type.
- SHOT: drag a rectangle anywhere on the virtual desktop. Escape/right-click
  cancels. Copy original pixels as PNG and bitmap.
- AUTO: toggle clicking. Adjacent AREA gear: select the saved click area.
- START: toggle login startup. PIN: keep open. Settings: options and Exit.

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
