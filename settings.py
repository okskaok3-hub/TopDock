# VDI Toolkit - Configuration and Settings

import json
import math
import os
from pathlib import Path

from platform_utils import get_config_dir

DEFAULT_CONFIG = {
    "paste_mode": "safe",
    "char_delay": 0.05,
    "press_duration": 0.02,
    "paste_hotkey": "ctrl+shift+v",
    "pause_hotkey": "ctrl+shift+p",
    "clicker_hotkey": "shift+alt+9",
    "click_delay_min": 60.0,
    "click_delay_max": 60.0,
    "click_area": [],
    "notify_enabled": True,
    "notify_overlay": True,
    "notify_position": "top-right",
    "notify_duration": 5,
    "notify_sound": False,
    "notify_sound_file": "",
    "trim_trailing_whitespace": True,
    "ai_provider": "openai",
    "ai_hotkey": "ctrl+shift+a",
    "ai_system_prompt": "Analyze the screenshot and answer clearly using the visible information.",
    "openai_api_key": "",
    "openai_model": "gpt-4.1-mini",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "start_with_windows": False,
}

PASTE_MODES = {
    "fast": {"char_delay": 0.02, "press_duration": 0.01},
    "safe": {"char_delay": 0.05, "press_duration": 0.02},
    "ultra_safe": {"char_delay": 0.10, "press_duration": 0.05},
}

VALID_NOTIFICATION_POSITIONS = {
    "top-right",
    "top-left",
    "bottom-right",
    "bottom-left",
}

VALID_AI_PROVIDERS = {
    "openai",
    "gemini",
}


class ConfigValidationError(ValueError):
    """Raised when a config update would create invalid state."""


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigValidationError(f"Expected boolean value, got {value!r}")


class Config:
    def __init__(self, config_dir=None):
        self.config_dir = Path(config_dir) if config_dir else get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.load_issues = []
        self.data = self._load()

    @staticmethod
    def normalize_hotkey(hotkey):
        if not isinstance(hotkey, str):
            raise ConfigValidationError("Hotkey must be a string")

        parts = []
        seen = set()
        aliases = {
            "control": "ctrl",
            "command": "win",
            "meta": "win",
            "super": "win",
            "cmd": "win",
        }

        for raw_part in hotkey.split("+"):
            part = raw_part.strip().lower()
            if not part:
                continue
            part = aliases.get(part, part)
            if part not in seen:
                seen.add(part)
                parts.append(part)

        if not parts:
            raise ConfigValidationError("Hotkey cannot be empty")

        if all(part in {"ctrl", "alt", "shift", "win"} for part in parts):
            raise ConfigValidationError("Hotkey must include a non-modifier key")

        return "+".join(parts)

    @classmethod
    def _validate_value(cls, key, value):
        if key == "paste_mode":
            if value not in PASTE_MODES:
                raise ConfigValidationError(f"Invalid paste mode: {value!r}")
            return value

        if key in {"char_delay", "press_duration", "click_delay_min", "click_delay_max"}:
            value = float(value)
            if not math.isfinite(value) or value <= 0:
                raise ConfigValidationError(f"{key} must be positive")
            max_value = 5.0 if key in {"char_delay", "press_duration"} else 86400.0
            if value > max_value:
                raise ConfigValidationError(f"{key} must be <= {max_value:g}")
            return value

        if key in {"paste_hotkey", "pause_hotkey", "clicker_hotkey", "ai_hotkey"}:
            return cls.normalize_hotkey(value)

        if key == "click_area":
            if value in (None, []):
                return []
            if not isinstance(value, (list, tuple)) or len(value) != 4:
                raise ConfigValidationError("click_area must contain x1, y1, x2, y2")
            coords = [int(item) for item in value]
            if coords[2] <= coords[0] or coords[3] <= coords[1]:
                raise ConfigValidationError("click_area must have positive width and height")
            return coords

        if key in {
            "notify_enabled",
            "notify_overlay",
            "notify_sound",
            "trim_trailing_whitespace",
            "start_with_windows",
        }:
            return _as_bool(value)

        if key == "notify_position":
            value = str(value).strip().lower()
            if value not in VALID_NOTIFICATION_POSITIONS:
                raise ConfigValidationError(f"Invalid notification position: {value!r}")
            return value

        if key == "notify_duration":
            value = int(value)
            if value < 1:
                raise ConfigValidationError("notify_duration must be >= 1")
            return value

        if key == "ai_provider":
            value = str(value).strip().lower()
            if value not in VALID_AI_PROVIDERS:
                raise ConfigValidationError(f"Invalid AI provider: {value!r}")
            return value

        if key in {
            "notify_sound_file",
            "ai_system_prompt",
            "openai_api_key",
            "openai_model",
            "gemini_api_key",
            "gemini_model",
        }:
            return str(value)

        raise ConfigValidationError(f"Unknown config key: {key}")

    @classmethod
    def validate_snapshot(cls, values, strict=False):
        merged = DEFAULT_CONFIG.copy()
        if values:
            merged.update(values)

        normalized = {}
        issues = []

        for key, default in DEFAULT_CONFIG.items():
            try:
                normalized[key] = cls._validate_value(key, merged.get(key, default))
            except (TypeError, ValueError, ConfigValidationError) as exc:
                if strict:
                    raise ConfigValidationError(str(exc)) from exc
                issues.append(f"{key}: {exc}")
                normalized[key] = default

        if normalized["click_delay_max"] < normalized["click_delay_min"]:
            message = "click_delay_max must be >= click_delay_min"
            if strict:
                raise ConfigValidationError(message)
            issues.append(message)
            normalized["click_delay_min"] = DEFAULT_CONFIG["click_delay_min"]
            normalized["click_delay_max"] = DEFAULT_CONFIG["click_delay_max"]

        return normalized, issues

    def _load(self):
        loaded = {}
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as file_handle:
                    loaded = json.load(file_handle)
                    if not isinstance(loaded, dict):
                        raise ConfigValidationError("Config file must contain a JSON object")
        except Exception as exc:
            print(f"Config load error: {exc}")

        data, issues = self.validate_snapshot(loaded, strict=False)
        self.load_issues = issues
        for issue in issues:
            print(f"Config validation warning: {issue}")
        return data

    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        temporary_file = self.config_file.with_name(f".{self.config_file.name}.tmp")
        try:
            with open(temporary_file, "w", encoding="utf-8") as file_handle:
                json.dump(self.data, file_handle, indent=2, sort_keys=True)
                file_handle.write("\n")
                file_handle.flush()
                os.fsync(file_handle.fileno())
            os.replace(temporary_file, self.config_file)
        except Exception:
            try:
                temporary_file.unlink()
            except OSError:
                pass
            raise

    def get(self, key, default=None):
        return self.data.get(key, default)

    def snapshot(self):
        return self.data.copy()

    def update(self, values):
        normalized, _issues = self.validate_snapshot({**self.data, **values}, strict=True)
        previous = self.data
        self.data = normalized
        try:
            self.save()
        except Exception:
            self.data = previous
            raise
        return self.snapshot()

    def set(self, key, value):
        if key not in DEFAULT_CONFIG:
            raise ConfigValidationError(f"Unknown config key: {key}")
        self.update({key: value})

    def reset_defaults(self):
        previous = self.data
        self.data = DEFAULT_CONFIG.copy()
        try:
            self.save()
        except Exception:
            self.data = previous
            raise
        return self.snapshot()

    def apply_paste_mode(self, mode):
        if mode not in PASTE_MODES:
            raise ConfigValidationError(f"Invalid paste mode: {mode!r}")
        self.update({
            "paste_mode": mode,
            "char_delay": PASTE_MODES[mode]["char_delay"],
            "press_duration": PASTE_MODES[mode]["press_duration"],
        })
        return self.snapshot()


config = Config()
