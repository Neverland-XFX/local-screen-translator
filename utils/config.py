import json
from pathlib import Path

from utils.paths import get_base_dir


DEFAULT_CONFIG_PATH = get_base_dir() / "config" / "default.json"
USER_CONFIG_PATH = get_base_dir() / "config" / "user.json"


def _deep_update(base: dict, overlay: dict) -> dict:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_config() -> dict:
    data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    if USER_CONFIG_PATH.exists():
        user = json.loads(USER_CONFIG_PATH.read_text(encoding="utf-8"))
        data = _deep_update(data, user)
    return data


def save_user_config(data: dict) -> None:
    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USER_CONFIG_PATH.exists():
        try:
            existing = json.loads(USER_CONFIG_PATH.read_text(encoding="utf-8"))
            data = _deep_update(existing, data)
        except json.JSONDecodeError:
            pass
    USER_CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8"
    )
