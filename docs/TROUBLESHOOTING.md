# Troubleshooting

## Dock process runs but no overlay appears

Move the pointer to the top edge or press Ctrl+Alt+Space. On Windows, use the
notification-area icon to reveal it. Launch from the logged-in desktop: a process
started in an isolated desktop can be responsive but invisible to the user.
On Linux, run in an X11 desktop session. An SSH connection needs the correct
DISPLAY and X authority; do not disable X authentication globally.

## Overlay does not cover full-screen VDI

TopDock requests topmost behavior, but exclusive compositor surfaces, secure
desktops and some VDI clients can block it. Try the reveal shortcut or the VDI
client's maximized/borderless mode. Wayland global input and overlay behavior is
not fully supported.

## Windows missing-library crash

Use the current self-contained release archive. Source builds must include WPF
native libraries. Do not reuse an EXE from a failed intermediate publish folder.

## Linux GLIBC version error

The Kali release requires glibc 2.42+. Build from source on the target system;
do not replace the operating system's libc to run TopDock.

## Application cards are missing

Linux requires `wmctrl` and `xprop` (`x11-utils`). Run `./TopDock-VDI --check` in
the desktop session. Window enumeration requires a compatible X11 window manager.

## Some text or symbols are absent

The current VDI fallback skips all non-ASCII characters and reports the count.
Arrows and emoji cannot stop the rest of the paste. Non-Latin text is not
supported by this mode. If letters have wrong capitalization, verify Caps Lock
and the host/guest keyboard layouts and avoid holding modifiers during typing.

## Newline/indentation differences

TopDock attempts to remove editor-generated indentation after Enter. Editors
with unusual Home/Delete behavior or auto-completion may still alter input.
Use a plain-text editor or turn off auto-indent/auto-completion when necessary.
For slow VDI connections, increase typing delays in the Toolkit settings.

## Screenshot is small or looks resized

Capture retains the selected physical dimensions. A small region is not a 4K
image. Capture the full 4K desktop to obtain 3840×2160. Some destination apps
scale previews or recompress pasted images; inspect actual image dimensions in
an image editor. Protected video/secure content may appear black.

## Linux screenshot/clipboard failure

Install `scrot` and `xclip`. Run as the desktop user, not root. Linux publishes
`image/png`; the destination must accept that clipboard format.

## Auto-clicker does not start

Select an area first, then toggle AUTO. Clicking is restricted to recognized VDI
clients in the foreground. Screenshot selection pauses clicking. Re-enable AUTO
after capture when needed.
