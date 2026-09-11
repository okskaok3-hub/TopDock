# TopDock v1.0.0

First repository release, combining Windows v5 and Linux v4.

## Included

- Compact top-edge dock with application-name cards and horizontal scrolling.
- Integrated VDI host clipboard typing and area-based auto-clicker.
- Region screenshot selection with original-resolution, lossless PNG output.
- Unsupported-symbol skipping with a reported count; the rest of the paste continues.
- Startup/pin controls and Settings creator credit.

## Downloads

- **TopDock-Windows-v5.zip:** self-contained Windows x64 executable.
- **TopDock-Linux-Kali-v4-x86_64.tar.gz:** Linux ELF built on Kali 2026.2,
  requiring x86-64, glibc 2.42+ and an X11 desktop.
- **SHA256SUMS.txt:** checksums for both executable archives.
- GitHub's source archives contain the documented current source tree.

For Linux install `wmctrl`, `x11-utils`, `xclip`, and `scrot`. Older distributions
should build from source. See README and LINUX.md for commands.

## Validation

Windows release build succeeded. Symbol filtering and pixel-exact 3840×2160 PNG
encoding checks passed. The updated Windows executable was relaunched and
confirmed responsive on the interactive desktop.

Linux paste lifecycle, filtering and capture tests passed. Isolated X11 tests
verified layout at 900/1200/1500px, overflow navigation, off-screen position,
PNG clipboard dimensions/pixels, native 4K capture, and executable window creation.

## Important behavior

Paste skips all non-ASCII characters (not only arrows). The completion message
reports the count. Screenshot size matches the selected physical pixels: smaller
regions are not enlarged. VDI clients and compositors may restrict overlays or
input. See troubleshooting documentation for details.

Historical feature changes are documented in CHANGELOG.md; this release does
not claim earlier local builds were separately tagged Git releases.
