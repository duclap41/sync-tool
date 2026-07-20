from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from config import config
from drive import DriveService
from launcher import MelonDSLauncher
from logger import get_logger
from models import SyncState
from monitor import SaveMonitor
from sync_engine import SyncEngine

log = get_logger(__name__)

# ---- Dark (modern) theme palette ----
BG = "#1e1e2e"          # main background
CARD = "#2a2a3e"        # card / secondary dialog background
ACCENT = "#e23b3b"      # pokeball red
ACCENT_HOVER = "#f24b4b"
TEXT = "#e6e6ea"
MUTED = "#9a9ab0"
OK = "#43d17a"
FONT = "Segoe UI"


def make_pokeball(size: int) -> tk.PhotoImage:
    """Draw a Pokémon pokeball icon in code, no external file needed."""
    img = tk.PhotoImage(width=size, height=size)

    c = size / 2
    R = size / 2 - 1

    RED = "#ee1515"
    WHITE = "#f5f5f5"
    BLACK = "#202028"

    outside = []
    rows = []

    outline = max(1.0, size * 0.06)

    for y in range(size):
        row = []
        for x in range(size):
            dx = x - c + 0.5
            dy = y - c + 0.5
            d = (dx * dx + dy * dy) ** 0.5

            if d > R:
                row.append(BG)
                outside.append((x, y))
                continue

            if d > R - outline:              # outer rim
                row.append(BLACK)
            elif d < size * 0.13:            # center button (white)
                row.append(WHITE)
            elif d < size * 0.20:            # black ring around button
                row.append(BLACK)
            elif abs(dy) < size * 0.085:     # black horizontal band
                row.append(BLACK)
            elif dy < 0:                     # top half red
                row.append(RED)
            else:                            # bottom half white
                row.append(WHITE)

        rows.append("{" + " ".join(row) + "}")

    img.put(" ".join(rows))

    for (x, y) in outside:
        img.transparency_set(x, y, True)

    return img


def center(win: tk.Misc, w: int, h: int):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 3
    win.geometry(f"{w}x{h}+{x}+{y}")


class MainWindow:

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("Pokémon Save Sync")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Pokeball icon for the window + taskbar
        self.icon = make_pokeball(48)
        self.root.iconphoto(True, self.icon)

        self._init_style()

        # ---- Content ----
        container = ttk.Frame(self.root, style="Bg.TFrame")
        container.pack(fill="both", expand=True, padx=24, pady=20)

        self.ball = make_pokeball(72)
        tk.Label(
            container,
            image=self.ball,
            bg=BG,
        ).pack(pady=(4, 6))

        ttk.Label(
            container,
            text="Pokémon Save Sync",
            style="Title.TLabel",
        ).pack()

        ttk.Button(
            container,
            text="▶  Start melonDS",
            style="Accent.TButton",
            command=lambda: self._run(launch=True),
        ).pack(fill="x", pady=(18, 8))

        ttk.Button(
            container,
            text="↻  Sync Now",
            style="Ghost.TButton",
            command=lambda: self._run(launch=False),
        ).pack(fill="x")

        # Status line: centered, highlighted
        self.status = tk.StringVar(value="● Ready")
        self.status_label = ttk.Label(
            container,
            textvariable=self.status,
            style="Status.TLabel",
            anchor="center",
            justify="center",
        )
        self.status_label.pack(fill="x", pady=(20, 2))

        center(self.root, 360, 400)

        # ---- Connect to Drive ----
        self.drive = DriveService()
        folder_id = self.drive.get_or_create_folder(config.drive_folder)
        self.sync_engine = SyncEngine(self.drive, folder_id)
        self.launcher = MelonDSLauncher(
            config.melonds_path,
            config.rom_path,
        )

    # ------------------------------------------------------------------ style
    def _init_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Bg.TFrame", background=BG)

        style.configure(
            "Title.TLabel",
            background=BG,
            foreground=TEXT,
            font=(FONT, 15, "bold"),
        )

        style.configure(
            "Status.TLabel",
            background=CARD,
            foreground=ACCENT,
            font=(FONT, 12, "bold"),
            padding=10,
        )

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="white",
            font=(FONT, 11, "bold"),
            borderwidth=0,
            padding=12,
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_HOVER), ("disabled", "#5a3a3a")],
            foreground=[("disabled", "#c9b0b0")],
        )

        style.configure(
            "Ghost.TButton",
            background=CARD,
            foreground=TEXT,
            font=(FONT, 11),
            borderwidth=0,
            padding=12,
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#37374f"), ("disabled", "#242433")],
            foreground=[("disabled", MUTED)],
        )

    # ------------------------------------------------------------ status utils
    def set_status(self, text: str, color: str = ACCENT):
        def apply():
            self.status.set(text)
            self.status_label.configure(foreground=color)

        self.root.after(0, apply)

    def _error(self, msg: str):
        self.root.after(
            0,
            lambda: messagebox.showerror("Pokémon Sync", msg),
        )

    # ---------------------------------------------------------------- workflow
    def _run(self, launch: bool):

        log.info("User clicked '%s'.", "Start melonDS" if launch else "Sync Now")

        def worker():
            try:
                self.set_status("● Checking local save…", MUTED)
                time.sleep(0.35)

                self.set_status("● Comparing with Google Drive…", MUTED)
                result = self.sync_engine.compare(config.save_path)
                log.info("Compare result: %s", result.state.name)
                time.sleep(0.35)

                if result.state == SyncState.IDENTICAL:
                    self.set_status("✓ IDENTICAL — already in sync", OK)
                else:
                    self.set_status(
                        f"● {result.state.name} — please choose a source",
                        MUTED,
                    )

                    choice = self._ask_choice(result)
                    log.info("User chose source: %s", choice or "Cancel")

                    if choice is None:
                        self.set_status("✕ Cancelled", MUTED)
                        return

                    if choice == "local":
                        self.set_status("⬆ Uploading PC save to Drive…", MUTED)
                        time.sleep(0.3)
                        self.sync_engine.upload(config.save_path)
                        self.set_status("✓ Done — Drive uses PC save", OK)
                    else:
                        self.set_status("⬇ Downloading Drive save…", MUTED)
                        time.sleep(0.3)
                        self.sync_engine.download(
                            config.save_path,
                            result.remote,
                        )
                        self.set_status("✓ Done — PC uses Drive save", OK)

                if launch:
                    time.sleep(0.3)
                    self.set_status("▶ Launching melonDS…", MUTED)
                    self.launcher.start()

                    monitor = SaveMonitor(
                        self.launcher,
                        self.sync_engine,
                        config.save_path,
                        config.check_interval,
                    )

                    self.set_status("● Playing — auto-syncing on changes…", ACCENT)
                    monitor.run()

                    self.set_status("✓ melonDS closed — finished", OK)

            except Exception as e:
                log.exception("Error during sync")
                self.set_status("✕ Error", ACCENT)
                self._error(str(e))

        threading.Thread(target=worker, daemon=True).start()

    # ---------------------------------------------------- choice dialog (modal)
    def _ask_choice(self, result):
        """Called from a worker thread; open the dialog on the main thread and wait for the result."""
        holder = {"val": None}
        done = threading.Event()

        def show():
            holder["val"] = self._choice_dialog(result)
            done.set()

        self.root.after(0, show)
        done.wait()
        return holder["val"]

    def _choice_dialog(self, result) -> str | None:
        local = result.local
        remote = result.remote
        has_local = local is not None
        has_remote = remote is not None

        hint = {
            SyncState.LOCAL_NEWER: "The PC save is newer.",
            SyncState.REMOTE_NEWER: "The Drive save is newer.",
            SyncState.LOCAL_MISSING: "No save on PC — only on Drive.",
            SyncState.REMOTE_MISSING: "No save on Drive — only on PC.",
        }.get(result.state, "The two sides differ.")

        def fmt(f):
            if f is None:
                return "— none —"
            when = f.modified.astimezone().strftime("%d/%m/%Y %H:%M")
            kind = "melonDS (.sav)" if f.name.lower().endswith(".sav") else "Delta (.dsv)"
            return f"{kind}\n{when}\n{f.size:,} bytes"

        dlg = tk.Toplevel(self.root)
        dlg.title("Choose a save")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self.root)

        choice = {"val": None}

        ttk.Label(
            dlg,
            text="The saves in the two places differ",
            style="Title.TLabel",
        ).pack(pady=(18, 2), padx=20)

        ttk.Label(
            dlg,
            text=hint + "  Choose the one to keep:",
            background=BG,
            foreground=MUTED,
            font=(FONT, 10),
        ).pack(pady=(0, 14), padx=20)

        cards = ttk.Frame(dlg, style="Bg.TFrame")
        cards.pack(padx=20, pady=(0, 6))

        def pick(v):
            choice["val"] = v
            dlg.destroy()

        def build_card(col, title, info, value, enabled, btn_text, style_name):
            frame = tk.Frame(cards, bg=CARD)
            frame.grid(row=0, column=col, padx=8, sticky="nsew")

            tk.Label(
                frame, text=title, bg=CARD, fg=TEXT,
                font=(FONT, 11, "bold"),
            ).pack(pady=(12, 4), padx=14)

            tk.Label(
                frame, text=info, bg=CARD,
                fg=TEXT if enabled else MUTED,
                font=(FONT, 9), justify="center",
            ).pack(padx=14)

            ttk.Button(
                frame,
                text=btn_text,
                style=style_name,
                command=lambda: pick(value),
                state=(tk.NORMAL if enabled else tk.DISABLED),
            ).pack(fill="x", padx=12, pady=12)

        build_card(
            0, "💻  PC (melonDS)", fmt(local), "local",
            has_local, "⬆  Use PC save",
            "Accent.TButton" if result.state == SyncState.LOCAL_NEWER else "Ghost.TButton",
        )
        build_card(
            1, "☁  Google Drive", fmt(remote), "remote",
            has_remote, "⬇  Use Drive save",
            "Accent.TButton" if result.state in (
                SyncState.REMOTE_NEWER, SyncState.LOCAL_MISSING,
            ) else "Ghost.TButton",
        )

        ttk.Button(
            dlg, text="Cancel", style="Ghost.TButton",
            command=lambda: pick(None),
        ).pack(fill="x", padx=20, pady=(4, 16))

        center(dlg, 440, 320)
        dlg.grab_set()
        dlg.wait_window()

        return choice["val"]

    def run(self):
        self.root.mainloop()
