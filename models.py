from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto


class SyncState(Enum):
    IDENTICAL = auto()

    LOCAL_NEWER = auto()

    REMOTE_NEWER = auto()

    LOCAL_MISSING = auto()

    REMOTE_MISSING = auto()


@dataclass(slots=True)
class DriveFile:
    id: str

    name: str

    md5: str

    size: int

    modified: datetime


@dataclass(slots=True)
class SyncResult:
    state: SyncState

    local: DriveFile | None

    remote: DriveFile | None


@dataclass(slots=True)
class Config:
    drive_folder: str

    save_path: str

    rom_path: str

    melonds_path: str

    check_interval: float = 5.0