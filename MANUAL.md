# VDI Toolkit User Manual

VDI Toolkit types clipboard text into the active VDI window one character at a time. It is useful when normal clipboard paste is blocked or unavailable.

Use this tool only with VDI environments and accounts you are authorized to operate.

## 1. Start the tool

### Run from Python

Open Command Prompt or PowerShell in the project folder and run:

```text
python main.py
```

On Windows, you can also double-click `run.bat`.

The application runs in the background with a system-tray icon. Open the tray menu and choose **Open Control Center** to view the main window.

### Run the packaged version

If an executable has been built, open the corresponding file inside the `dist` folder, such as:

```text
dist\VDIToolkit.exe
```

## 2. Basic keyword workflow

1. Copy the keyword or text on the local computer.
2. Click inside the target field in the VDI.
3. Start typing with the paste hotkey:

   ```text
   Ctrl+Shift+V
   ```

4. Keep the target VDI field focused while the text is being sent.
5. Wait for the **Paste complete!** notification.

The tool reads the local clipboard once at the start, so changes to the clipboard while typing do not change the active operation.

## 3. Paste controls

### Start or paste now

- Hotkey: `Ctrl+Shift+V`
- Control Center: **Dashboard > Paste Now**
- Tray menu: **Clipboard Paste > Paste Now**

Only one paste can run at a time. A second trigger is rejected while the first operation is active.

### Pause and resume

- Hotkey: `Ctrl+Shift+P`
- Control Center: **Clipboard > Pause / Resume**
- Tray menu: **Clipboard Paste > Pause / Resume**

The status changes to **Paused**. Press the same hotkey or button again to continue.

### Cancel

- Hotkey: `Esc`
- Control Center: **Clipboard > Cancel Paste**
- Tray menu: **Clipboard Paste > Cancel Paste**

Cancellation stops the operation between characters and also cancels the initial delay before typing begins.

`Esc` also stops the auto-clicker when it is running.

## 4. Paste modes

Open **Control Center > Clipboard**.

- **Fast**: quickest typing; use only when the VDI reliably accepts injected keystrokes.
- **Safe**: recommended default for most VDI systems.
- **Ultra Safe**: slowest, but gives the remote session more time to process each character.

If characters are missing, switch to **Safe** or **Ultra Safe** and try again.

## 5. Timing settings

The Clipboard section contains:

- **Character Delay**: wait time between characters.
- **Press Duration**: how long each key is held.
- **Trim trailing spaces/newlines**: removes whitespace at the end of clipboard text. Disable this when trailing whitespace is meaningful.

Start with the default Safe mode. Increase the delays if the VDI drops characters or responds slowly.

## 6. Hotkeys

Default hotkeys:

| Action | Default hotkey |
|---|---|
| Send clipboard text | `Ctrl+Shift+V` |
| Pause/resume paste | `Ctrl+Shift+P` |
| Cancel paste | `Esc` |
| Toggle auto-clicker | `Shift+Alt+9` |
| AI screenshot | `Ctrl+Shift+A` |

Hotkeys can be changed in the Control Center. Do not assign the same hotkey to multiple actions.

After changing a hotkey, use **Apply Clipboard Settings** and test it before relying on it in the VDI.

## 7. Text and keyboard limitations

The tool sends keyboard events rather than using the VDI clipboard. Results depend on:

- The active keyboard layout.
- The VDI client and remote application.
- Remote-session latency.
- Whether the target field accepts Enter, Tab, symbols, or special characters.

ASCII letters, numbers, common symbols, spaces, tabs, and newlines are supported. Some Unicode characters, emoji, and characters unavailable on the active keyboard layout may fail and will produce an error notification.

Always verify important values after sending them.

## 8. Auto-clicker

The auto-clicker is separate from keyword sending.

1. Open **Control Center > Dashboard**.
2. Choose **Select Click Area**.
3. Drag over the target area and release.
4. Use the clicker hotkey or **Start/Stop Clicker**.
5. Press `Esc` to stop it.

Use this only where automated clicking is permitted. Do not leave it running unattended in an unintended window.

## 9. AI screenshot assistant

The AI feature captures a screenshot and sends it to the configured provider. Before using it:

- Confirm that sending VDI screenshots externally is permitted.
- Do not include confidential information unless approved.
- Configure the provider and API key in **Control Center > AI**.

The AI feature is not required for keyword sending.

## 10. Notifications and tray behavior

Closing the Control Center hides the window but leaves the toolkit running. Reopen it from the system tray.

Use the tray menu to:

- Open the Control Center.
- Change paste mode.
- Start, pause, resume, or cancel a paste.
- Select and control the auto-clicker.
- Configure AI screenshots.
- Enable or disable notifications.
- Enable **Float over full-screen VDI** to keep notification cards above a
  borderless or browser-based full-screen VDI session without taking focus
  away from the remote session.
- Exit the application.

The overlay is a custom in-app card rather than a standard Windows toast, so it
can remain visible over normal topmost/full-screen VDI windows. Exclusive
DirectX full-screen applications and the Windows secure desktop can still hide
desktop overlays; use borderless or browser full-screen mode when this is
required.

## 11. Configuration

Settings are stored in a platform-specific `VDIToolkit` configuration folder. Use **Advanced Configuration > Open Config Folder** to open it.

The application validates settings and writes configuration changes atomically. If a save fails, the in-memory settings are rolled back.

Do not share the configuration file if it contains API keys.

## 12. Troubleshooting

### Nothing happens when I press the hotkey

- Confirm that the toolkit is running in the system tray.
- Check the displayed hotkey in the Control Center.
- Try running the packaged executable or Python process with the required permissions.
- Check whether another application already uses the same hotkey.
- Restart the toolkit after changing keyboard permissions.

### Characters are missing

- Switch to Safe or Ultra Safe mode.
- Increase Character Delay and Press Duration.
- Check the remote keyboard layout.
- Avoid unsupported Unicode characters.
- Try a short test keyword first.

### Text goes into the wrong window

- Press `Esc` immediately to cancel.
- Click the correct VDI field before starting.
- Use the initial delay to confirm focus before typing begins.
- Keep the VDI window visible while sending text.

### Paste will not stop

- Press `Esc`.
- Use **Cancel Paste** in the Control Center or tray menu.
- If necessary, exit the toolkit; shutdown now requests cancellation and waits briefly for the paste worker to stop.

### Tkinter or dependency errors appear

Run:

```text
python -m unittest discover -s tests -v
```

Then install or repair the dependencies listed in `requirements.txt`.

## 13. Recommended first test

Before using real keywords:

1. Open a harmless text field in the VDI.
2. Copy `TEST-123`.
3. Press `Ctrl+Shift+V`.
4. Pause with `Ctrl+Shift+P`.
5. Resume with `Ctrl+Shift+P`.
6. Test cancellation with a longer sample and `Esc`.
7. Confirm the final text matches the source exactly.
