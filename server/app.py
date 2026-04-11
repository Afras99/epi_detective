"""
Entry point for the OpenEnv validator — loads app from epi_detective/server/app.py
via importlib to avoid circular imports with this server/ package name.
"""
import importlib.util
import sys
from pathlib import Path

_root = Path(__file__).parent.parent
_target = _root / "epi_detective" / "server" / "app.py"

# Add epi_detective/ to sys.path so its internal imports resolve
_pkg = str(_root / "epi_detective")
if _pkg not in sys.path:
    sys.path.insert(0, _pkg)

_spec = importlib.util.spec_from_file_location("_epi_server_app", _target)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

app = _mod.app


def main(host: str = "0.0.0.0", port: int = 7860):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
