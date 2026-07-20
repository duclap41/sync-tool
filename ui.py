from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from config import config
from drive import DriveService
from launcher import MelonDSLauncher
from monitor import SaveMonitor
from sync_engine import SyncEngine


class MainWindow:

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("Pokemon Save Sync")
        self.root.geometry("420x180")
        self.root.resizable(False, False)

        self.status = tk.StringVar(value="Ready.")

        tk.Button(
            self.root,
            text="Start melonDS",
            width=30,
            command=self.start_clicked,
        ).pack(pady=(20, 8))

        tk.Button(
            self.root,
            text="Sync Now",
            width=30,
            command=self.sync_clicked,
        ).pack()

        tk.Label(
            self.root,
            textvariable=self.status,
            anchor="w",
        ).pack(fill="x", padx=20, pady=20)

        self.drive = DriveService()

        folder_id = self.drive.get_or_create_folder(
            config.drive_folder
        )

        self.sync_engine = SyncEngine(
            self.drive,
            folder_id,
        )

        self.launcher = MelonDSLauncher(
            config.melonds_path,
            config.rom_path,
        )

    def set_status(self, text: str):

        self.root.after(
            0,
            lambda: self.status.set(text),
        )

    def sync_clicked(self):

        def worker():

            try:

                self.set_status("Syncing...")

                result = self.sync_engine.sync(
                    config.save_path,
                )

                self.set_status(
                    f"{result.state.name}"
                )

            except Exception as e:

                self.set_status("Error")

                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Sync",
                        str(e),
                    ),
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def start_clicked(self):

        def worker():

            try:

                self.set_status("Checking save...")

                result = self.sync_engine.sync(
                    config.save_path,
                )

                self.set_status(
                    f"{result.state.name}"
                )

                self.launcher.start()

                monitor = SaveMonitor(
                    self.launcher,
                    self.sync_engine,
                    config.save_path,
                    config.check_interval,
                )

                monitor.run()

                self.set_status("Finished.")

            except Exception as e:

                self.set_status("Error")

                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Pokemon Sync",
                        str(e),
                    ),
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def run(self):

        self.root.mainloop()