from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path
from models import DriveFile

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive"]


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
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file,
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)

            Path(self.token_file).write_text(creds.to_json(), encoding="utf8")

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

    def get_or_create_folder(self, name: str) -> str:
        result = self.service.files().list(
            q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id,name)",
        ).execute()

        files = result.get("files", [])
        if files:
            return files[0]["id"]

        folder = self.service.files().create(
            body={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
        ).execute()

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

    def get_remote_info(self, folder_id: str, filename: str):
        f = self.find_file(folder_id, filename)
        if f is None:
            return None

        return DriveFile(
            id=f["id"],
            name=f["name"],
            md5=f.get("md5Checksum", ""),
            size=int(f.get("size", 0)),
            modified=datetime.fromisoformat(
                f["modifiedTime"].replace("Z", "+00:00")
            ).replace(tzinfo=None),
        )

    def local_info(self, path: Path):
        if not path.exists():
            return None

        return DriveFile(
            id="",
            name=path.name,
            md5=self.md5(path),
            size=path.stat().st_size,
            modified=datetime.fromtimestamp(path.stat().st_mtime),
        )

    def upload(self, folder_id: str, path: Path):
        media = MediaFileUpload(str(path), resumable=True)
        remote = self.find_file(folder_id, path.name)

        if remote:
            return self.service.files().update(
                fileId=remote["id"],
                media_body=media,
                fields="id",
            ).execute()["id"]

        return self.service.files().create(
            body={
                "name": path.name,
                "parents": [folder_id],
            },
            media_body=media,
            fields="id",
        ).execute()["id"]

    def download(self, file_id: str, output: Path):
        request = self.service.files().get_media(fileId=file_id)

        with output.open("wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
