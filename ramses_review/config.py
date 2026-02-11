"""Configuration management for Ramses Review."""

import json
import os
import platform
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_CONFIG = {
    "review": {
        "default_collection_path": "",  # Relative to project root, e.g., "for_review"
    },
}


def get_config_dir() -> Path:
    """Get the Ramses Review configuration directory."""
    home = Path.home()
    config_dir = home / ".ramses"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the path to the Review configuration file."""
    return get_config_dir() / "review_config.json"


def get_ramses_config_dir() -> Path:
    """Get the common Ramses configuration directory (shared by all tools)."""
    system = platform.system()
    if system == 'Windows':
        config_dir = Path(os.path.expandvars('${APPDATA}/Ramses/Config'))
    elif system == 'Linux':
        config_dir = Path.home() / '.config' / 'Ramses' / 'Config'
    elif system == 'Darwin':  # macOS
        config_dir = Path.home() / 'Library' / 'Application Support' / 'Ramses' / 'Config'
    else:
        # Fallback
        config_dir = Path.home() / '.config' / 'Ramses' / 'Config'

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_ramses_config_path() -> Path:
    """Get the path to the common Ramses settings file."""
    return get_ramses_config_dir() / "ramses_addons_settings.json"


def load_config() -> Dict[str, Any]:
    """Load Review configuration from disk, or create default if not exists."""
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            # Merge with defaults (in case new keys were added)
            return {**DEFAULT_CONFIG, **config}
        except Exception:
            pass

    # Create default config
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    """Save Review configuration to disk."""
    try:
        config_path = get_config_path()
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def load_ramses_settings() -> Dict[str, Any]:
    """Load settings from the common Ramses config (shared by all tools)."""
    config_path = get_ramses_config_path()

    default_settings = {
        "clientPath": "",
        "clientPort": 18185,
    }

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            return {
                "clientPath": settings.get("clientPath", ""),
                "clientPort": settings.get("clientPort", 18185),
            }
        except Exception:
            pass

    return default_settings


def save_ramses_settings(client_path: Optional[str] = None, client_port: Optional[int] = None) -> bool:
    """Save settings to the common Ramses config (shared by all tools)."""
    config_path = get_ramses_config_path()

    # Load existing settings to preserve other values
    existing = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    # Update only the specified values
    if client_path is not None:
        existing["clientPath"] = client_path
    if client_port is not None:
        existing["clientPort"] = client_port

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=4)
        return True
    except Exception:
        return False
