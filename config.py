from __future__ import annotations

import json
from pathlib import Path

from models import Config

BASE_DIR = Path(__file__).resolve().parent

CONFIG_FILE = BASE_DIR / "config.json"

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def _require_file(path: Path, name: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{name} not found:\n{path}")
    return path


def load_config() -> Config:

    if not CONFIG_FILE.exists():
        raise FileNotFoundError("config.json not found.")

    with CONFIG_FILE.open(
        "r",
        encoding="utf8",
    ) as f:
        raw = json.load(f)

    save_path = Path(raw["save_path"])

    return Config(
        drive_folder=raw["drive_folder"],

        # Save file is NOT required to exist yet
        save_path=str(save_path),

        # These two files are required
        rom_path=str(
            _require_file(
                Path(raw["rom_path"]),
                "ROM",
            )
        ),

        melonds_path=str(
            _require_file(
                Path(raw["melonds_path"]),
                "melonDS",
            )
        ),

        check_interval=float(
            raw.get(
                "check_interval",
                5,
            )
        ),
    )


config = load_config()