# TopDock

TopDock is a native Windows floating taskbar for quickly switching between local and VDI windows.

## Quick start

1. Run `TopDock.exe`. No installer or separate .NET download is required for the self-contained build.
2. Move the pointer against the top edge of any monitor whenever you want to reveal it.
3. To keep it available after restarting Windows, open Settings in TopDock and enable **Launch when I sign in**.

## Use

- Paste skips unsupported non-ASCII symbols such as `→` and emoji and reports
  the skipped count. All non-ASCII letters are also skipped. ASCII code, tabs,
  and line breaks are preserved; the host clipboard is not changed. `A→B`
  becomes `AB`, without adding replacement characters.
- Screenshot output includes lossless PNG and standard bitmap clipboard
  formats, at the selected region's original pixel dimensions. Full 4K captures
  remain 3840×2160; smaller regions are not enlarged.

- Move the pointer into the top 14 pixels of any monitor to reveal TopDock. The wider trigger and explicit topmost promotion are designed to work over full-screen Citrix/VDI sessions.
- Click a window card to switch to it.
- Window cards show only the friendly application name; full document and page titles are intentionally hidden for a cleaner dock.
- The premium compact layout uses uniform 140 × 44 pixel cards, framed icons, hover-only shortcut hints, and a slim active-window accent.
- Drag the slim slider below the window cards—or scroll over the strip—to reach
  every open application.
- Select **SHOT**, then drag anywhere across the complete Windows desktop to
  capture a specific region. The image is copied directly to the host clipboard;
  press `Esc` or right-click to cancel.
- Press `Ctrl+Alt+Space` to show or hide TopDock.
- Press `Alt+1` through `Alt+9` while TopDock is focused to switch directly.
- Middle-click a window card to request that the window close.
- Use the pin control to temporarily disable auto-hide.
- Use Settings to launch TopDock at sign-in or enable compact window cards.
- Settings includes the creator credit: **Made with love by Aditya Rathee**.
- Select **PASTE** to capture the host Windows text clipboard, restore Citrix or Remote Desktop, and type the captured text as physical keystrokes. This does not send `Ctrl+Shift+V` into the VDI, so it cannot accidentally use the remote session's clipboard. New lines and source-code indentation are preserved by clearing editor-generated auto-indent before each clipboard line. Modifier keys are redundantly released with VDI-safe timing so capital letters and shifted punctuation do not affect following characters. Character and key-press delays follow the VDI Toolkit's safe-paste settings.
- Select the auto-clicker's adjacent **gear** and drag a rectangle to save the click area. Select **AUTO** to toggle clicking ON or OFF. It clicks at the configured interval only while Citrix or Remote Desktop is foreground and restores the cursor after each click.
- Select **STARTUP** to start TopDock when you sign in to Windows. A check mark indicates that startup is enabled.

TopDock runs in the notification area. Double-click its tray icon to reveal it, or right-click the icon to open the menu.

Only one copy of TopDock can run at a time. It does not send window titles or usage data anywhere.

## Build

Requires the .NET 10 SDK on Windows.

```powershell
dotnet build -c Release
dotnet publish -c Release
```
