"""Re-export from the convergence module to avoid package/module conflict."""

from __future__ import annotations

import importlib.util
from pathlib import Path

# The parent directory contains convergence.py (the actual module)
# This package shadows it. Re-export everything from the .py file.
_mod_path = str(Path(__file__).parent.parent / "convergence.py")
_spec = importlib.util.spec_from_file_location("app.ml._convergence_mod", _mod_path)
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

    # Re-export all public names
    for _name in dir(_mod):
        if not _name.startswith("_"):
            globals()[_name] = getattr(_mod, _name)
