"""OS shell helpers: open folder in file manager, etc."""

import os
import subprocess
import sys


def open_path_in_explorer(path: str) -> bool:
    """Open path in the system file manager (folder or file's parent). Returns True if launched."""
    if not path or not os.path.exists(path):
        return False
    target = os.path.dirname(path) if os.path.isfile(path) else path
    try:
        if sys.platform == "win32":
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.run(["open", target], check=False)
        else:
            subprocess.run(["xdg-open", target], check=False)
        return True
    except Exception:
        return False
