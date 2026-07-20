from __future__ import annotations

import subprocess
from pathlib import Path


class MelonDSLauncher:

    def __init__(
        self,
        melonds_path: str,
        rom_path: str,
    ):

        self.melonds = Path(
            melonds_path
        )

        self.rom = Path(
            rom_path
        )

        self.process: subprocess.Popen | None = None

    @property
    def is_running(self) -> bool:

        if self.process is None:
            return False

        return self.process.poll() is None

    def start(self):

        if self.is_running:
            return self.process

        self.process = subprocess.Popen(
            [
                str(self.melonds),
                # "-f", this only fullscreen the first window, not all of them
                str(self.rom),
            ]
        )

        return self.process

    def wait(self):

        if self.process is None:
            return

        self.process.wait()

    def stop(self):

        if not self.is_running:
            return

        self.process.terminate()

        try:

            self.process.wait(
                timeout=5
            )

        except subprocess.TimeoutExpired:

            self.process.kill()

    def exit_code(self):

        if self.process is None:
            return None

        return self.process.poll()