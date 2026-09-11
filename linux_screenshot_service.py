"""Capture a Linux/X11 screenshot and publish it as PNG clipboard data."""

from dataclasses import dataclass
from io import BytesIO
import shutil
import subprocess


@dataclass(frozen=True)
class ScreenshotResult:
    success: bool
    message: str


class LinuxScreenshotService:
    def __init__(self, screenshotter=None, runner=None, command_finder=None):
        self._screenshotter = screenshotter
        self._runner = runner or subprocess.run
        self._command_finder = command_finder or shutil.which

    def _capture(self, region=None):
        if self._screenshotter:
            if callable(self._screenshotter):
                return self._screenshotter(region)
            return self._screenshotter
        import pyautogui

        return pyautogui.screenshot(region=region)

    def capture_to_clipboard(self, region=None):
        if not self._command_finder("xclip"):
            return ScreenshotResult(False, "Install xclip to copy screenshots")

        try:
            image = self._capture(region)
            if region and image.size != (region[2], region[3]):
                return ScreenshotResult(False, "Capture size mismatch; original pixels could not be preserved")
            png = BytesIO()
            image.save(png, format="PNG")
            payload = png.getvalue()
            if not payload:
                return ScreenshotResult(False, "Screenshot capture returned no image")

            result = self._runner(
                ["xclip", "-selection", "clipboard", "-t", "image/png", "-i"],
                input=payload,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            if result.returncode != 0:
                error = getattr(result, "stderr", b"")
                if isinstance(error, bytes):
                    error = error.decode("utf-8", errors="replace")
                return ScreenshotResult(False, str(error).strip() or "xclip rejected the screenshot")
            return ScreenshotResult(True, f"Original PNG copied: {image.width} × {image.height}px")
        except Exception as exc:
            return ScreenshotResult(False, f"Screenshot failed: {exc}")
