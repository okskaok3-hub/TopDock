import unittest
from pathlib import Path

from settings import Config, ConfigValidationError, DEFAULT_CONFIG


class MemoryConfig(Config):
    def __init__(self, initial_data=None):
        self.config_dir = Path(".")
        self.config_file = Path("memory-config.json")
        self.load_issues = []
        self.data, self.load_issues = self.validate_snapshot(initial_data or {}, strict=False)

    def save(self):
        return None


class ConfigTests(unittest.TestCase):
    def make_config(self, initial_data=None):
        return MemoryConfig(initial_data)

    def test_invalid_values_fall_back_to_defaults(self):
        cfg = self.make_config({
            "paste_mode": "warp_speed",
            "click_delay_min": 10,
            "click_delay_max": 1,
            "notify_duration": 0,
        })

        self.assertEqual(cfg.get("paste_mode"), DEFAULT_CONFIG["paste_mode"])
        self.assertEqual(cfg.get("click_delay_min"), DEFAULT_CONFIG["click_delay_min"])
        self.assertEqual(cfg.get("click_delay_max"), DEFAULT_CONFIG["click_delay_max"])
        self.assertEqual(cfg.get("notify_duration"), DEFAULT_CONFIG["notify_duration"])
        self.assertTrue(cfg.load_issues)

    def test_update_normalizes_hotkeys(self):
        cfg = self.make_config()
        cfg.update({"paste_hotkey": " Ctrl + Shift + V "})
        self.assertEqual(cfg.get("paste_hotkey"), "ctrl+shift+v")

    def test_update_rejects_invalid_delay_range(self):
        cfg = self.make_config()
        with self.assertRaises(ConfigValidationError):
            cfg.update({"click_delay_min": 5, "click_delay_max": 1})

    def test_reset_defaults_restores_clean_snapshot(self):
        cfg = self.make_config()
        cfg.update({"notify_duration": 8, "notify_position": "bottom-left"})
        reset = cfg.reset_defaults()
        self.assertEqual(reset["notify_duration"], DEFAULT_CONFIG["notify_duration"])
        self.assertEqual(reset["notify_position"], DEFAULT_CONFIG["notify_position"])

    def test_invalid_ai_provider_falls_back_to_default(self):
        cfg = self.make_config({"ai_provider": "anthropic"})
        self.assertEqual(cfg.get("ai_provider"), DEFAULT_CONFIG["ai_provider"])
        self.assertTrue(cfg.load_issues)

    def test_non_finite_delays_are_rejected(self):
        cfg = self.make_config()
        with self.assertRaises(ConfigValidationError):
            cfg.update({"char_delay": float("nan")})
        with self.assertRaises(ConfigValidationError):
            cfg.update({"press_duration": float("inf")})

    def test_pause_hotkey_and_trim_setting_are_supported(self):
        cfg = self.make_config()
        cfg.update({"pause_hotkey": " Ctrl + Shift + P ", "trim_trailing_whitespace": False})
        self.assertEqual(cfg.get("pause_hotkey"), "ctrl+shift+p")
        self.assertFalse(cfg.get("trim_trailing_whitespace"))

    def test_notification_overlay_setting_is_supported(self):
        cfg = self.make_config()
        cfg.update({"notify_overlay": False})
        self.assertFalse(cfg.get("notify_overlay"))

    def test_click_area_is_validated_and_preserved(self):
        cfg = self.make_config({"click_area": [-100, 20, 300, 220]})
        self.assertEqual(cfg.get("click_area"), [-100, 20, 300, 220])

        invalid = self.make_config({"click_area": [10, 10, 5, 5]})
        self.assertEqual(invalid.get("click_area"), [])
        self.assertTrue(invalid.load_issues)


if __name__ == "__main__":
    unittest.main()
