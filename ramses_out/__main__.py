"""Entry point for Ramses Out."""

# APPLY RUNTIME PATCHES
try:
    from . import ramses_patches
    ramses_patches.apply()
except ImportError:
    print("[Ramses] Warning: ramses_patches module not found. Critical fixes may be missing.")

from .gui import main

if __name__ == "__main__":
    main()
