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

    def _newest_remote(
        self,
        base_name: str,
    ) -> DriveFile | None:
        """Lấy file save mới nhất trên Drive, xét cả .sav lẫn .dsv."""

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

        # Xét mọi file save cùng tên gốc trên Drive rồi lấy bản mới nhất.
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

        # Chỉ so md5/size khi remote cùng định dạng (.sav) với local.
        # Với .dsv thì nội dung byte khác (có footer) nên không so trực tiếp.
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

        self.drive.upload(
            self.folder_id,
            local_path,
        )

        # Sau khi đẩy .sav của melonDS lên, dọn các bản save khác (vd .dsv cũ
        # từ iPhone) để trên Drive chỉ còn đúng 1 file mới nhất là .sav.
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

        # Nếu chưa được truyền remote (vd gọi trực tiếp) thì tự tìm bản mới nhất.
        if remote is None:
            remote = self._newest_remote(
                local_path.stem,
            )

        if remote is None:

            raise FileNotFoundError(
                "Remote save not found."
            )

        # melonDS cần .sav: nếu bản mới nhất là .dsv thì convert trước khi ghi
        # vào save_path để melonDS mở nhanh, khỏi tự convert lúc load.
        if remote.name.lower().endswith(".dsv"):

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