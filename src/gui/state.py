"""Application state and configuration with JSON persistence."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CONFIG_FILE = DATA_DIR / "config.json"


@dataclass
class AppConfig:
    tunee_url: str = "https://www.tunee.ai"
    output_dir: str = "~/Downloads/tunee"
    monitor_index: int = 3
    max_songs: int = 50
    max_scrolls: int = 15
    click_delay: float = 1.5
    between_songs_delay: float = 3.0
    video_wait_max: int = 90
    dl_icon_threshold: float = 0.7
    modal_row_threshold: float = 0.7
    video_dl_threshold: float = 0.7

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> AppConfig:
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass
        return cls()


@dataclass
class AppState:
    config: AppConfig = field(default_factory=AppConfig)
    downloaded: int = 0
    duplicates: int = 0
    failures: int = 0
    running: bool = False


_state: AppState | None = None


def get_state() -> AppState:
    """Singleton access to application state."""
    global _state
    if _state is None:
        _state = AppState(config=AppConfig.load())
    return _state
