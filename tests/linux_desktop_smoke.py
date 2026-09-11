"""Run under xvfb-run: exercise real Tk geometry and X11 PNG clipboard."""
import io
import sys
import time
import subprocess
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from PIL import Image
from linux_topdock import LinuxTopDock

root = tk.Tk()
app = LinuxTopDock(root)
app.window_service.list_windows = lambda: [SimpleNamespace(
    application=name, is_vdi=False, window_id=str(i)) for i, name in enumerate(
    ["Firefox", "Terminal", "File Manager", "Citrix Workspace", "Text Editor", "Settings", "Very long application name"])]
app.pinned = True
root.update()
app._refresh_windows(schedule=False)
root.update()
for width in (900, 1200, 1500):
    app.width = width
    app._set_geometry(0)
    root.update()
    app._update_window_scrollregion()
    root.update()
    assert app.window_canvas.winfo_height() == 44
    assert app.window_scrollbar.winfo_height() == 12
    assert app.window_canvas.winfo_width() > 80
    for slot, card, _ in app.card_slots:
        assert card.winfo_height() == 44
        assert slot.winfo_height() == 44
    assert app.shot_button.winfo_rootx() + app.shot_button.winfo_width() < root.winfo_rootx() + width
    app.window_canvas.xview_moveto(1)
    root.update()
    assert app.window_canvas.xview()[1] > 0.99
    print(f"PASS layout {width}px, slider reaches final card")
app._set_geometry(-72)
root.update()
assert root.winfo_y() == -72, root.winfo_y()
app.capture_busy = True
app.is_shown = False
app.reveal()
assert not app.is_shown
app.capture_busy = False
app.show_settings()
root.update()
assert any(isinstance(w, tk.Label) and "Aditya Rathee" in w.cget("text") for w in app.settings_window.winfo_children())
app.settings_window.destroy()
app.settings_window = None
app._set_geometry(0)
root.update()
from linux_screenshot_service import LinuxScreenshotService
service = LinuxScreenshotService(screenshotter=lambda region: Image.new("RGB", (region[2], region[3]), "#a855f7"))
result = service.capture_to_clipboard((10, 20, 80, 40))
assert result.success, result.message
data = subprocess.check_output(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"], timeout=5)
im = Image.open(io.BytesIO(data))
assert im.size == (80, 40)
assert im.getpixel((0, 0)) == (168, 85, 247)
print("PASS PNG clipboard readback, dimensions and pixels")
result = LinuxScreenshotService().capture_to_clipboard((20, 20, 100, 50))
assert result.success, result.message
data = subprocess.check_output(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"], timeout=5)
assert Image.open(io.BytesIO(data)).size == (100, 50)
print("PASS real X11 region screenshot")
if root.winfo_screenwidth() >= 3840 and root.winfo_screenheight() >= 2160:
    result = LinuxScreenshotService().capture_to_clipboard((0, 0, 3840, 2160))
    assert result.success, result.message
    data = subprocess.check_output(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"], timeout=10)
    assert Image.open(io.BytesIO(data)).size == (3840, 2160)
    print("PASS native 4K capture and lossless PNG clipboard readback: 3840 x 2160")
app.exit()
