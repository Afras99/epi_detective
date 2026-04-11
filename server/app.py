"""
Thin re-export so the validator can find server.app:app at the repo root.
All logic lives in epi_detective/server/app.py.
"""
import sys
from pathlib import Path

# Make epi_detective/ importable
_pkg = Path(__file__).parent.parent / "epi_detective"
if str(_pkg) not in sys.path:
    sys.path.insert(0, str(_pkg))

from server.app import app, main  # noqa: F401  # re-export

__all__ = ["app", "main"]
