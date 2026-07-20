from __future__ import annotations

import hashlib
import io
import os
from datetime import datetime, timezone
from pathlib import Path
from models import DriveFile
from logger import get_logger

log = get_logger(__name__)

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive"]

# Save file extensions the tool recognizes (melonDS = .sav, Delta/DeSmuME = .dsv)
SAVE_EXTENSIONS = (".sav", ".dsv")

# Footer structure of a .dsv file, taken from j-tai/dsv2sav
# https://github.com/j-tai/dsv2sav/blob/master/dsv2sav.py
DSV_FOOTER = b"|<--Snip above here to create a raw sav by excluding this DeSmuME savedata footer:"
DSV_COOKIE = b"|-DESMUME SAVE-|"
DSV_FOOTER_LEN = len(DSV_FOOTER) + 24 + len(DSV_COOKIE)


class DriveService:
    def __init__(
        self,
        credentials_file: str = "google-credentials.json",
        token_file: str = "token.json",
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = self._login()

    def _login(self):
        creds = None

        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(
                self.token_file,
                SCOPES,
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                log.info("Drive token expired -> refreshing.")
                creds.refresh(Request())
            else:
                log.info("No valid token -> opening browser to sign in to Google.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file,
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)

            Path(self.token_file).write_text(creds.to_json(), encoding="utf8")

        log.info("Connected to Google Drive.")
        return build("drive", "v3", credentials=creds)

    @staticmethod
    def md5(path: Path) -> str:
        h = hashlib.md5()
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def dsv_to_sav(data: bytes) -> bytes:
        """Convert .dsv (DeSmuME) data to raw .sav by stripping the footer.

        Logic taken from j-tai/dsv2sav: the footer is always at the end of the
        file and ends with the cookie ``|-DESMUME SAVE-|``; the .sav part is all
        the bytes before it.
        """
        footer = data[-DSV_FOOTER_LEN:]
        if not footer.endswith(DSV_COOKIE):
            raise ValueError("Invalid DSV data (cookie mismatch)")
        return data[:-DSV_FOOTER_LEN]

    def get_or_create_folder(self, name: str) -> str:
        result = self.service.files().list(
            q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id,name)",
        ).execute()

        files = result.get("files", [])
        if files:
            log.info("Using existing Drive folder: %s", name)
            return files[0]["id"]

        folder = self.service.files().create(
            body={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
        ).execute()

        log.info("Created new Drive folder: %s", name)
        return folder["id"]

    def find_file(self, folder_id: str, filename: str):
        result = self.service.files().list(
            q=f"'{folder_id}' in parents and name='{filename}' and trashed=false",
            fields="files(id,name,md5Checksum,size,modifiedTime)",
        ).execute()

        files = result.get("files", [])
        if not files:
            return None
        return files[0]

    @staticmethod
    def _to_drivefile(f: dict) -> DriveFile:
        # Drive's modifiedTime is UTC (trailing "Z") -> parse into a datetime
        # with UTC tzinfo so it compares correctly with local time (also UTC).
        return DriveFile(
            id=f["id"],
            name=f["name"],
            md5=f.get("md5Checksum", ""),
            size=int(f.get("size", 0)),
            modified=datetime.fromisoformat(
                f["modifiedTime"].replace("Z", "+00:00")
            ),
        )

    def get_remote_info(self, folder_id: str, filename: str):
        f = self.find_file(folder_id, filename)
        if f is None:
            return None

        return self._to_drivefile(f)

    def list_saves(self, folder_id: str, base_name: str) -> list[DriveFile]:
        """List all save files (both .sav and .dsv) with the same base name in the folder."""
        names = " or ".join(
            f"name='{base_name}{ext}'" for ext in SAVE_EXTENSIONS
        )

        result = self.service.files().list(
            q=f"'{folder_id}' in parents and ({names}) and trashed=false",
            fields="files(id,name,md5Checksum,size,modifiedTime)",
        ).execute()

        saves = [self._to_drivefile(f) for f in result.get("files", [])]
        log.info(
            "Found %d save file(s) on Drive: %s",
            len(saves),
            [s.name for s in saves],
        )
        return saves

    def local_info(self, path: Path):
        if not path.exists():
            return None

        return DriveFile(
            id="",
            name=path.name,
            md5=self.md5(path),
            size=path.stat().st_size,
            # Keep the same UTC (aware) standard as Drive's modifiedTime.
            modified=datetime.fromtimestamp(
                path.stat().st_mtime,
                tz=timezone.utc,
            ),
        )

    def upload(self, folder_id: str, path: Path):
        media = MediaFileUpload(str(path), resumable=True)
        remote = self.find_file(folder_id, path.name)

        if remote:
            log.info("Updating existing file on Drive: %s", path.name)
            return self.service.files().update(
                fileId=remote["id"],
                media_body=media,
                fields="id",
            ).execute()["id"]

        log.info("Creating new file on Drive: %s", path.name)
        return self.service.files().create(
            body={
                "name": path.name,
                "parents": [folder_id],
            },
            media_body=media,
            fields="id",
        ).execute()["id"]

    def download(self, file_id: str, output: Path):
        log.info("Downloading file from Drive: %s", output.name)
        request = self.service.files().get_media(fileId=file_id)

        with output.open("wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

    def trash(self, file_id: str):
        log.info("Moving old file to Drive trash (id=%s).", file_id)
        # Move to trash (safe, recoverable) instead of permanently deleting.
        self.service.files().update(
            fileId=file_id,
            body={"trashed": True},
        ).execute()

    def download_bytes(self, file_id: str) -> bytes:
        log.info("Downloading .dsv from Drive into memory to convert (id=%s).", file_id)
        request = self.service.files().get_media(fileId=file_id)

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue()
