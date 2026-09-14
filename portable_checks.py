"""Opt-in isolated-display checks for the self-contained Linux executable."""
import io
import os
import shutil
import subprocess
import sys
from PIL import Image
from linux_screenshot_service import LinuxScreenshotService


def run():
    bundle = getattr(sys, "_MEIPASS", "")
    for tool in ("wmctrl", "xprop", "xclip", "scrot"):
        path = shutil.which(tool)
        assert path and path.startswith(os.path.join(bundle, "bin")), (tool, path)
        print("Bundled helper:", tool)
    result = LinuxScreenshotService().capture_to_clipboard((0, 0, 3840, 2160))
    assert result.success, result.message
    png = subprocess.check_output(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"], timeout=10)
    assert Image.open(io.BytesIO(png)).size == (3840, 2160)
    print("PASS bundled helpers and original-resolution 4K PNG clipboard capture")
