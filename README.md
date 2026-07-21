# Pokémon Save Sync

A small desktop tool that keeps a Nintendo DS Pokémon save file in sync between
a **Windows PC (melonDS)** and an **iPhone (Delta emulator)** through **Google Drive**.

It launches melonDS, watches the save file while you play, and uploads changes to
Google Drive. When the newest save on Drive was made on the iPhone (a `.dsv` file
from Delta/DeSmuME), it automatically converts it to the `.sav` format melonDS
uses, so you never have to convert saves by hand.

## Features

- Two-way sync of a single save between PC and iPhone via Google Drive.
- Understands both formats: melonDS `.sav` and Delta/DeSmuME `.dsv`.
- Automatically converts `.dsv → .sav` on download (no external tools needed).
- Picks the **newest** save on Drive (comparing `.sav` and `.dsv`) before syncing.
- When the two sides differ, asks you which one to keep (PC or Drive).
- After uploading from the PC, keeps only one latest `.sav` on Drive.
- Rotating log file at `logs/sync.log`.

## Requirements

- Windows 10/11
- [melonDS](https://melonds.kuribo64.net/) and your Pokémon ROM
- A Google account and a Google Cloud OAuth client (see step 3)
- [uv](https://docs.astral.sh/uv/) (installed below)

## Setup

### 1. Install uv

`uv` manages the Python version and dependencies for you.

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or with WinGet:

```powershell
winget install --id=astral-sh.uv -e
```

Close and reopen the terminal, then verify:

```powershell
uv --version
```

### 2. Install dependencies

From the project folder, let uv create the virtual environment and install
everything (it also downloads the correct Python version automatically):

```powershell
uv sync
```

### 3. Google Drive credentials

The tool needs an OAuth client to access your Google Drive:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create
   a project (or use an existing one).
2. Enable the **Google Drive API**.
3. Under **APIs & Services → Credentials**, create an **OAuth client ID** of type
   **Desktop app**.
4. Download the JSON and save it in the project folder as **`google-credentials.json`**.

On the first run, a browser window opens asking you to sign in and grant access.
After that, a `token.json` file is created and reused, so you won't be asked again.

### 4. Configure `config.json`

Edit `config.json` to match your machine:

```json
{
    "drive_folder": "PokemonSync",
    "save_path": "E:\\...\\Pokemon - Black Version.sav",
    "rom_path": "E:\\...\\Pokemon - Black Version.nds",
    "melonds_path": "E:\\...\\melonDS.exe",
    "check_interval": 5
}
```

- `drive_folder` — name of the folder created on Google Drive.
- `save_path` — where melonDS stores the `.sav` (does not need to exist yet).
- `rom_path` — your Pokémon ROM (`.nds`).
- `melonds_path` — path to `melonDS.exe`.
- `check_interval` — seconds between save checks while playing.

## Run

### From a terminal

```powershell
uv run python main.py
```

### One-click on Windows

Two launchers are included; just **double-click** one:

- **`run.vbs`** (recommended) — starts the app with **no console window at all**.
- **`run.bat`** — same thing, but a command window may flash for a moment (a `.bat`
  file always opens a console briefly; that is a Windows limitation).

Both use `uvw` + `pythonw`, the "windowless" variants of `uv` and Python, so no
terminal stays open. You still get full output in `logs/sync.log`.

`run.bat`:

```bat
@echo off
cd /d "%~dp0"
start "" uvw run pythonw main.py
```

`run.vbs`:

```vbs
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "uvw run pythonw main.py", 0, False   ' 0 = hidden window
```

Prefer a visible console while debugging? Run `uv run python main.py` in a
terminal instead.

Tip: right-click `run.vbs` → **Send to → Desktop (create shortcut)** to get a
desktop icon.

## Logs

Everything the tool does is written to `logs/sync.log` (and printed to the
console). The log rotates automatically, so it never grows without bound. If
something goes wrong, check this file first.
