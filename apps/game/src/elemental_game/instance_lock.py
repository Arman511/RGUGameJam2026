from __future__ import annotations

import errno
import os
from pathlib import Path
from typing import BinaryIO

from elemental_game.database.local_database import get_default_data_dir


class GameInstanceLock:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path) if path is not None else get_default_data_dir() / "game.lock"
        )
        self._file: BinaryIO | None = None

    def acquire(self) -> bool:
        if self._file is not None:
            return True

        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.path.open("a+b")
        try:
            self._lock_file(lock_file)
        except OSError as error:
            lock_file.close()
            if error.errno in (errno.EACCES, errno.EAGAIN):
                return False
            raise

        try:
            lock_file.seek(0)
            lock_file.truncate()
            lock_file.write(f"{os.getpid()}\n".encode("ascii"))
            lock_file.flush()
        except BaseException:
            self._unlock_file(lock_file)
            lock_file.close()
            raise

        self._file = lock_file
        return True

    def release(self) -> None:
        lock_file = self._file
        if lock_file is None:
            return
        self._file = None
        try:
            lock_file.seek(0)
            lock_file.truncate()
            if os.name == "nt":
                lock_file.write(b"\0")
                lock_file.flush()
            self._unlock_file(lock_file)
        finally:
            lock_file.close()

    @staticmethod
    def _lock_file(lock_file: BinaryIO) -> None:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            if not lock_file.read(1):
                lock_file.seek(0)
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        elif os.name == "posix":
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            raise OSError(f"Unsupported platform for process locks: {os.name}")

    @staticmethod
    def _unlock_file(lock_file: BinaryIO) -> None:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        elif os.name == "posix":
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
