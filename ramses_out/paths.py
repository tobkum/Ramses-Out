"""Shared path resolution for the Ramses Out package.

Importing this module has the side effect of inserting the Ramses API library
onto ``sys.path`` (if not already present), making it safe to import as the
first statement in any module that needs the shared Ramses library.

Attributes
----------
DEV_ROOT : Path
    In development: the ``Ramses-Dev/`` root that contains ``lib/``,
    ``Ramses-Out/``, etc.
    In a frozen build: the directory containing the Out executable.
"""

import sys
from pathlib import Path


def _compute_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # Development layout:
    #   this file  →  Ramses-Out/ramses_out/paths.py
    #   .parent    →  Ramses-Out/ramses_out/
    #   .parent²   →  Ramses-Out/
    #   .parent³   →  Ramses-Dev/
    return Path(__file__).resolve().parent.parent.parent


#: Root directory used for all sibling-package lookups.
DEV_ROOT: Path = _compute_root()

for _p in (DEV_ROOT / "lib",):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
