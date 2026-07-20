from __future__ import annotations

from pathlib import Path

from drive import DriveService
from models import (
    DriveFile,
    SyncResult,
    SyncState,
)


class SyncEngine:

    def __init__(
        self,
        drive: DriveService,
        folder_id: str,
    ):

        self.drive = drive
        self.folder_id = folder_id

    def compare(
        self,
        local_path: str | Path,
    ) -> SyncResult:

        local_path = Path(local_path)

        local = self.drive.local_info(
            local_path
        )

        remote = self.drive.get_remote_info(
            self.folder_id,
            local_path.name,
        )

        if local is None and remote is None:

            raise FileNotFoundError(
                "No local or remote save found."
            )

        if local is None:

            return SyncResult(
                state=SyncState.LOCAL_MISSING,
                local=None,
                remote=remote,
            )

        if remote is None:

            return SyncResult(
                state=SyncState.REMOTE_MISSING,
                local=local,
                remote=None,
            )

        if (
            local.md5 == remote.md5
            and
            local.size == remote.size
        ):

            return SyncResult(
                state=SyncState.IDENTICAL,
                local=local,
                remote=remote,
            )

        if local.modified > remote.modified:

            return SyncResult(
                state=SyncState.LOCAL_NEWER,
                local=local,
                remote=remote,
            )

        return SyncResult(
            state=SyncState.REMOTE_NEWER,
            local=local,
            remote=remote,
        )

    def upload(
        self,
        local_path: str | Path,
    ):

        local_path = Path(local_path)

        self.drive.upload(
            self.folder_id,
            local_path,
        )

    def download(
        self,
        local_path: str | Path,
    ):

        local_path = Path(local_path)

        remote = self.drive.get_remote_info(
            self.folder_id,
            local_path.name,
        )

        if remote is None:

            raise FileNotFoundError(
                "Remote save not found."
            )

        self.drive.download(
            remote.id,
            local_path,
        )

    def sync(
        self,
        local_path: str | Path,
    ) -> SyncResult:

        result = self.compare(
            local_path
        )

        if result.state == SyncState.IDENTICAL:
            return result

        if result.state == SyncState.LOCAL_NEWER:
            self.upload(local_path)
            return result

        if result.state == SyncState.REMOTE_NEWER:
            self.download(local_path)
            return result

        if result.state == SyncState.REMOTE_MISSING:
            self.upload(local_path)
            return result

        if result.state == SyncState.LOCAL_MISSING:
            self.download(local_path)
            return result

        return result