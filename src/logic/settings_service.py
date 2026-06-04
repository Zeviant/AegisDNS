"""Per-user settings storage.

Settings live in src/VT_Cache/settings.json with the structure:

    {
        "nico":  { "theme": "Dark", "mute_notifications": false, ... },
        "sebas": { ... }
    }

Anything not stored falls back to DEFAULT_SETTINGS.
"""
import os
import json
from pathlib import Path
from typing import Any

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "VT_Cache" / "settings.json"

DEFAULT_SETTINGS = {
    "mute_notifications": False,
    "theme": "Default",
    "cache_invalidation_enabled": True,
    "cache_max_age_days": 30,
    "packet_alert_enabled": True,
    "packet_alert_threshold_10s": 12000,
    "packet_alert_cooldown_seconds": 60,
}


def _load_all() -> dict:
    try:
        if not SETTINGS_FILE.exists():
            return {}
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        # Reject legacy flat format (any top-level non-dict value).
        if data and any(not isinstance(v, dict) for v in data.values()):
            return {}
        return data
    except Exception:
        return {}


def _save_all(data: dict) -> None:
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(SETTINGS_FILE) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, SETTINGS_FILE)
    except Exception:
        pass


def get_user_settings(user_name: str) -> dict:
    """Return the user's settings, merged on top of DEFAULT_SETTINGS."""
    data = _load_all()
    user_data = data.get(user_name)
    if not isinstance(user_data, dict):
        user_data = {}
    return {**DEFAULT_SETTINGS, **user_data}


def get_setting(user_name: str, key: str, default: Any = None) -> Any:
    settings = get_user_settings(user_name)
    if default is None:
        default = DEFAULT_SETTINGS.get(key)
    return settings.get(key, default)


def set_setting(user_name: str, key: str, value: Any) -> None:
    data = _load_all()
    if not isinstance(data.get(user_name), dict):
        data[user_name] = {}
    data[user_name][key] = value
    _save_all(data)
