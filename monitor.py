from __future__ import annotations

import hashlib
import time
from pathlib import Path

from launcher import MelonDSLauncher
from logger import get_logger
from sync_engine import SyncEngine

log = get_logger(__name__)


class SaveMonitor:

    def __init__(
        self,
        launcher: MelonDSLauncher,
        sync_engine: SyncEngine,
        save_path: str,
        interval: float = 5.0,
    ):
        self.launcher = launcher
        self.sync = sync_engine
        self.save_path = Path(save_path)
        self.interval = interval
        self.last_hash: str | None = None

    def md5(self) -> str | None:

        if not self.save_path.exists():
            return None

        h = hashlib.md5()

        with self.save_path.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)

        return h.hexdigest()

    def upload_if_changed(self):

        current = self.md5()

        if current is None:
            return

        if current == self.last_hash:
            return

        try:
            self.sync.upload(self.save_path)
            self.last_hash = current
            log.info("[Monitor] Save changed -> uploaded to Drive.")
        except Exception:
            log.exception("[Monitor] Error while uploading save")

    def run(self):

        log.info("[Monitor] Start watching save every %.1fs.", self.interval)

        self.last_hash = self.md5()

        while self.launcher.is_running:
            self.upload_if_changed()
            time.sleep(self.interval)

        # Final sync when melonDS closes
        self.upload_if_changed()

        log.info("[Monitor] melonDS closed -> stop watching.")