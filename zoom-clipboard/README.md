# Zoom Clipboard dashboard

This is the Windows desktop source for the optional Zoom Clipboard dashboard
bundled with TopDock. It builds as a self-contained `ZoomClipboardUI.exe` and
is launched from the TopDock ZOOM button. TopDock checks for an executable beside
it first; Settings can point to another local copy.

Build on Windows with the .NET 10 SDK:

```powershell
dotnet publish ZoomClipboardUI.csproj -c Release -o ../release/windows
```

Sign-in and any upload are controlled by the dashboard itself. No user tokens,
stored sign-in state, or clipboard data are bundled in the release. The client
identifier in source is a public OAuth application identifier, not a secret.
This EXE does not run natively on Linux; Linux TopDock keeps its local clipboard
preview.
