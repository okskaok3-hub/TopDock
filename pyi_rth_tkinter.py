import os
import sys
from pathlib import Path


def _set_tk_environment():
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    tcl_dir = base_dir / "tcl" / "tcl8.6"
    tk_dir = base_dir / "tcl" / "tk8.6"

    if tcl_dir.exists():
        os.environ["TCL_LIBRARY"] = str(tcl_dir)
    if tk_dir.exists():
        os.environ["TK_LIBRARY"] = str(tk_dir)


_set_tk_environment()
