from __future__ import annotations

from pathlib import Path

from drive import DriveService
from logger import get_logger
from models import (
    DriveFile,
    SyncResult,
    SyncState,
)

log = get_logger(__name__)


class SyncEngine:

    def __init__(
        self,
        drive: DriveService,
        folder_id: str,
    ):

        self.drive = drive
        self.folder_id = folder_id

    def _newest_remote(
        self,
        base_name: str,
    ) -> DriveFile | None:
        """Get the newest save file on Drive, considering both .sav and .dsv."""

        remotes = self.drive.list_saves(
            self.folder_id,
            base_name,
        )

        if not remotes:
            return None

        return max(
            remotes,
            key=lambda r: r.modified,
        )

    def compare(
        self,
        local_path: str | Path,
    ) -> SyncResult:

        local_path = Path(local_path)

        local = self.drive.local_info(
            local_path
        )

        # Consider every save file with the same base name on Drive, then take the newest.
        remote = self._newest_remote(
            local_path.stem,
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

        # Only compare md5/size when the remote is the same format (.sav) as local.
        # A .dsv has different bytes (it has a footer), so it can't be compared directly.
        if (
            remote.name.lower().endswith(".sav")
            and
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

        log.info("Uploading PC save to Drive: %s", local_path.name)

        self.drive.upload(
            self.folder_id,
            local_path,
        )

        # After pushing the melonDS .sav up, clean up other saves (e.g. the old
        # .dsv from iPhone) so Drive keeps only one latest file: the .sav.
        self._keep_only(
            local_path.stem,
            local_path.name,
        )

    def _keep_only(
        self,
        base_name: str,
        keep_name: str,
    ):

        for remote in self.drive.list_saves(
            self.folder_id,
            base_name,
        ):

            if remote.name != keep_name:
                self.drive.trash(remote.id)

    def download(
        self,
        local_path: str | Path,
        remote: DriveFile | None = None,
    ):

        local_path = Path(local_path)

        # If no remote was passed (e.g. called directly), find the newest one.
        if remote is None:
            remote = self._newest_remote(
                local_path.stem,
            )

        if remote is None:

            raise FileNotFoundError(
                "Remote save not found."
            )

        # melonDS needs .sav: if the newest is a .dsv, convert it before writing
        # to save_path so melonDS opens fast without converting on load.
        if remote.name.lower().endswith(".dsv"):

            log.info("Newest is .dsv -> convert to .sav and write to local.")

            data = self.drive.download_bytes(
                remote.id,
            )

            local_path.write_bytes(
                self.drive.dsv_to_sav(data),
            )

            return

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
            self.download(local_path, result.remote)
            return result

        if result.state == SyncState.REMOTE_MISSING:
            self.upload(local_path)
            return result

        if result.state == SyncState.LOCAL_MISSING:
            self.download(local_path, result.remote)
            return result

        return result