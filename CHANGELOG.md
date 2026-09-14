# Changelog

## v1.1.0 — Portable Linux executable — 2026-09-14

- Provide a single downloadable `TopDock-Linux-x86_64` ELF executable, without
  an installer or shell launcher.
- Lower the Linux compatibility baseline from Kali/glibc 2.42 to glibc 2.31.
- Bundle Python, Tk, wmctrl, xprop, xclip, scrot and its PNG codec; resolve
  helpers from the extracted bundle before host utilities.
- Add container build recipes, clean-environment verification, startup checks
  and native 3840×2160 PNG clipboard readback checks.
- Keep the previous dock, paste, auto-clicker, screenshot and Settings features.
- Include the unchanged Windows v5 portable ZIP alongside Linux in v1.1.0,
  with combined checksums and platform-specific release instructions.
- Target x86-64 X11/glibc desktops; this is not an ARM/musl/Wayland build.

## v1.0.0 — Initial repository release — 2026-09-11

Packages: **Windows v5**, **Linux v4 (Kali x86-64)**.
The initial commit imports the current maintained source; earlier development
stages below are reconstructed from the project history, not separate Git tags.

### Current Windows v5 / Linux v4

- Skip unsupported Unicode symbols, including `→` and emoji, and report the
  skipped count. Continue typing the remaining text instead of failing midway.
- Preserve ASCII code, tabs and normalized line endings. Do not substitute arrows
  with operators or modify the host clipboard.
- Explicit original-resolution image output. Windows publishes lossless PNG plus
  bitmap; Linux publishes PNG and rejects a mismatched capture size.
- Prevent TopDock from reappearing or being promoted above screenshot selection.
- Pause auto-clicking during screenshot selection.
- Use physical pointer coordinates for Windows screenshot regions.
- Verify 3840×2160 PNG encoding/pixel fidelity on Windows and native 4K capture
  with clipboard readback in an isolated Linux X11 display.

### Linux v3 — Layout and executable release

- Replace crowded packing with a dedicated 44px card row and separate 12px
  slider hit area containing a subtle 4px visual track.
- Fit whole cards within the available width; constrain controls to pixel sizes.
- Add Settings and “Made with love by Aditya Rathee”.
- Correct negative geometry so auto-hide moves above the desktop instead of
  anchoring the dock to the bottom edge.
- Suspend reveal/topmost behavior while selecting or capturing a screenshot.
- Send worker results through a main-thread queue instead of calling Tk from
  background threads.
- Fix `wmctrl -lx` field parsing, hexadecimal window-ID comparison, and split
  window-state requests into the two-property limit supported by wmctrl.
- Avoid inherited subprocess output pipes blocking the xclip clipboard owner.
- Build the first tested ELF executable on Kali 2026.2 x86-64.
- Validate layout at 900, 1200, and 1500px, slider reachability, original PNG
  dimensions/pixels, off-screen coordinates, and frozen executable startup.

### Windows v4 — Scrolling, capture and layout refinement

- Expose horizontal scrolling through a visible application slider.
- Add SHOT with a full-desktop, multi-monitor crosshair region selector.
- Copy screenshot images to the host clipboard; Escape/right-click cancels.
- Add Settings creator credit.
- Correct packaging to include native WPF libraries in the self-contained EXE.
- Replace the oversized default scrollbar with a controlled template so cards
  are not vertically clipped; use a 4px thumb in a separate row.
- Fit complete cards across the viewport and align tool buttons.
- Verify the overlay on the interactive Windows desktop rather than treating
  a running process in an isolated desktop as proof that it is visible.

### Linux v2 — Region screenshots and window slider

- Add a visible horizontal window slider and wheel navigation.
- Add SHOT to capture a user-selected desktop rectangle and copy PNG via xclip.
- Add region forwarding tests and installation checks for capture utilities.

### Earlier Windows integrated builds / initial Linux port

- Three-section auto-hiding dock: identity, open applications and quick tools.
- Application-name labels in place of full document/window titles.
- Compact premium cards, focus/hover states and active-window accents on Windows.
- Top-edge reveal and Ctrl+Alt+Space recovery shortcut.
- Improve topmost promotion and the Windows activation band for full-screen VDI.
- Add login startup and pin controls.
- Capture host clipboard text before focusing VDI; remove dependence on the
  remote Ctrl+Shift+V clipboard operation.
- Preserve code line breaks and clear editor-generated indentation.
- Add redundant modifier releases and settling delays to reduce shifted/capital
  characters leaking into later input.
- Replace the separate VDI Toolkit launcher with an integrated auto-clicker:
  ON/OFF, saved area selection, and checks that a VDI client is foreground.
- Port dock and input helpers to Linux X11, with source installers, diagnostics,
  build scripts and documented Wayland restrictions.

## Known limits

- Unicode paste deliberately skips all non-ASCII characters; see README.
- Portable Linux binary requires glibc 2.31+ and X11. Legacy v1.0.0 requires 2.42+.
- Secure/exclusive desktop surfaces may cover overlays or block screen capture.
- A screenshot cannot exceed the detail present in the source screen pixels.
- Versions in historical filenames are local build revisions, not semantic API
  compatibility guarantees. Old experimental binaries are not promoted as releases.
