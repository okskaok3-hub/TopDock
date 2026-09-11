"""Run with xvfb-run to verify the frozen executable creates its X11 window."""
import subprocess
import time
from pathlib import Path

binary = Path(__file__).resolve().parents[1] / "dist-linux" / "TopDock-VDI"
process = subprocess.Popen([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    time.sleep(4)
    assert process.poll() is None, process.communicate()[0]
    tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
    assert "TopDock Linux" in tree, tree
    print("PASS standalone binary remains running and creates its TopDock X11 window")
finally:
    if process.poll() is None:
        process.terminate()
    output = process.communicate(timeout=10)[0]
    assert "Traceback" not in output, output
