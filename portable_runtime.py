"""Expose bundled desktop helpers before runtime dependency checks."""
import os
import sys

if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
    bundle = getattr(sys, "_MEIPASS", "")
    if bundle:
        os.environ["PATH"] = os.path.join(bundle, "bin") + os.pathsep + os.environ.get("PATH", "")
        os.environ["IMLIB2_LOADER_PATH"] = os.path.join(bundle, "imlib2", "loaders")
