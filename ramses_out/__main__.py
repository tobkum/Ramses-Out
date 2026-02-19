"""Entry point for Ramses Out."""

# Apply upstream API patches before any ramses code is imported.
from . import monkeypatches  # noqa: F401

from .gui import main

if __name__ == "__main__":
    main()
