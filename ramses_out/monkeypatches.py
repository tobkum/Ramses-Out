"""Ramses-Out-side patches for upstream Ramses API bugs.

Must be imported **before** any ramses package code runs (i.e. as the very
first import in ``__main__.py``) so patches are applied before singletons
are first constructed.

Current patches
---------------
macOS / Darwin – RamSettings._folderPath never set upstream (TODO stub).
  The upstream ``else: #TODO Darwin  pass`` branch leaves ``_folderPath``
  undefined, causing ``os.makedirs(cls._folderPath)`` to crash immediately.
  We inject the correct platform path before ``instance()`` is ever called.
"""

import os
import platform
import sys
from pathlib import Path

# Ensure lib/ is on sys.path before attempting to import ramses.ram_settings.
# __main__.py imports us before gui.py, so the module-level sys.path additions
# in gui.py / scanner.py / tracker.py have not run yet.
_lib_path = Path(__file__).resolve().parent.parent.parent / "lib"
if str(_lib_path) not in sys.path:
    sys.path.insert(0, str(_lib_path))


def _patch_ram_settings_darwin() -> None:
    """Set the missing Darwin config path on RamSettings before first use."""
    if platform.system() != "Darwin":
        return

    try:
        from ramses.ram_settings import RamSettings  # type: ignore[import]
    except ImportError:
        return  # Ramses not on path — singleton warmup in gui.py will retry.

    if getattr(RamSettings, "_instance", None) is not None:
        return  # Already initialised; patch no longer needed.

    _darwin_config = os.path.expanduser(
        "~/Library/Application Support/Ramses/Config"
    )

    _original_instance = RamSettings.__dict__["instance"].__func__

    @classmethod  # type: ignore[misc]
    def _patched_instance(cls):
        if cls._instance is None:
            cls._folderPath = _darwin_config
        return _original_instance(cls)

    RamSettings.instance = _patched_instance


_patch_ram_settings_darwin()
