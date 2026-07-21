from __future__ import annotations

import os
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

        # Fix melonDS 1.0's Qt high-DPI bug: on Windows display scales other
        # than 100%, screens are scaled incorrectly and leave a few pixels of
        # border in fullscreen. Setting QT_ENABLE_HIGHDPI_SCALING=0 fixes it.
        # See https://github.com/melonDS-emu/melonDS/issues/2208
        env = os.environ.copy()
        env["QT_ENABLE_HIGHDPI_SCALING"] = "0"

        self.process = subprocess.Popen(
            [
                str(self.melonds),
                # "-f", this only fullscreen the first window, not all of them
                str(self.rom),
            ],
            env=env,
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