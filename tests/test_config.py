"""Tests for configuration management."""

import os
import sys
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ramses_out import config


class TestConfig(unittest.TestCase):
    """Test configuration loading and saving."""

    def setUp(self):
        """Create temp config directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "out_config.json"
        self.ramses_config_file = Path(self.temp_dir) / "ramses_addons_settings.json"

    def test_default_config(self):
        """Test default configuration structure."""
        self.assertIn("review", config.DEFAULT_CONFIG)
        self.assertIn("default_collection_path", config.DEFAULT_CONFIG["review"])

    def test_load_config_creates_default(self):
        """Test loading config creates default if not exists."""
        with patch.object(config, 'get_config_path', return_value=self.config_file):
            loaded = config.load_config()

            self.assertEqual(loaded["review"]["default_collection_path"], "")
            self.assertTrue(self.config_file.exists())

    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        test_config = {
            "review": {
                "default_collection_path": "for_review",
            }
        }

        with patch.object(config, 'get_config_path', return_value=self.config_file):
            success = config.save_config(test_config)
            self.assertTrue(success)

            loaded = config.load_config()
            self.assertEqual(loaded["review"]["default_collection_path"], "for_review")

    def test_load_ramses_settings_default(self):
        """Test loading Ramses settings returns defaults."""
        with patch.object(config, 'get_ramses_config_path', return_value=self.ramses_config_file):
            settings = config.load_ramses_settings()

            self.assertEqual(settings["clientPath"], "")
            self.assertEqual(settings["clientPort"], 18185)

    def test_save_ramses_settings(self):
        """Test saving Ramses settings."""
        with patch.object(config, 'get_ramses_config_path', return_value=self.ramses_config_file):
            success = config.save_ramses_settings(
                client_path="C:/Ramses/Ramses.exe",
                client_port=18200
            )

            self.assertTrue(success)
            self.assertTrue(self.ramses_config_file.exists())

            # Verify saved content
            with open(self.ramses_config_file) as f:
                data = json.load(f)

            self.assertEqual(data["clientPath"], "C:/Ramses/Ramses.exe")
            self.assertEqual(data["clientPort"], 18200)

    def test_save_ramses_settings_preserves_other_values(self):
        """Test saving Ramses settings preserves other keys."""
        # Create initial config with extra keys
        initial = {
            "clientPath": "old/path",
            "clientPort": 18185,
            "otherSetting": "preserved",
        }

        self.ramses_config_file.write_text(json.dumps(initial))

        with patch.object(config, 'get_ramses_config_path', return_value=self.ramses_config_file):
            config.save_ramses_settings(client_port=18200)

            # Load and verify
            with open(self.ramses_config_file) as f:
                data = json.load(f)

            self.assertEqual(data["clientPort"], 18200)
            self.assertEqual(data["otherSetting"], "preserved")

    def test_config_dir_creation(self):
        """Test config directory creation."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            config_dir = config.get_config_dir()
            self.assertTrue(config_dir.exists())
            self.assertEqual(config_dir.name, ".ramses")

    def test_corrupted_config_fallback(self):
        """Test fallback to default on corrupted config."""
        # Write invalid JSON
        self.config_file.write_text("invalid json {")

        with patch.object(config, 'get_config_path', return_value=self.config_file):
            loaded = config.load_config()

            # Should return default config
            self.assertEqual(loaded, config.DEFAULT_CONFIG)

    def test_partial_config_merge(self):
        """Test config with some keys present."""
        # Save config with some keys
        partial = {
            "review": {
                "default_collection_path": "custom_path",
            }
        }

        self.config_file.write_text(json.dumps(partial))

        with patch.object(config, 'get_config_path', return_value=self.config_file):
            loaded = config.load_config()

            # Should have the custom value
            self.assertEqual(loaded["review"]["default_collection_path"], "custom_path")

    def tearDown(self):
        """Clean up temp directories."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
