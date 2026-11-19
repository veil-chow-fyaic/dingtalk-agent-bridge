"""Serialize validated importer records and keep one current public PR JSON file (macOS/Linux)."""
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
from uuid import uuid4


def publish(directory, name, record):
    directory = Path(directory)
    if not directory.is_absolute() or directory.resolve() != directory:
        raise ValueError("Choose a canonical operator-owned directory")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,38}\+[a-z0-9][a-z0-9_.-]{0,99}\+[1-9][0-9]*\.json", name):
        raise ValueError("Invalid PR snapshot name")
    root = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        # Cooperating importers lock the same directory inode. Process death releases this lock.
        fcntl.flock(root, fcntl.LOCK_EX)
        try:
            prior = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
        except FileNotFoundError:
            previous = None
        else:
            with os.fdopen(prior, "rb") as stream:
                if not stat.S_ISREG(os.fstat(prior).st_mode):
                    raise ValueError("Prior PR snapshot is not a regular file")
                data = stream.read(4097)
            if len(data) > 4096:
                raise ValueError("Prior PR snapshot exceeds its maximum size")
            previous = json.loads(data)
        if previous is not None:
            if previous["asOf"] > record["asOf"]:
                return False
            if previous["asOf"] == record["asOf"]:
                if previous.get("data") != record["data"]:
                    raise ValueError("Conflicting PR snapshots have the same acquisition time")
                # An identical manually imported record can gain a same-response collection receipt.
                if "acquisition" in previous or "acquisition" not in record:
                    return False

        tmp = "." + uuid4().hex + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=root)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(json.dumps(record, separators=(",", ":")).encode() + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, name, src_dir_fd=root, dst_dir_fd=root)
            os.fsync(root)
        finally:
            try:
                os.unlink(tmp, dir_fd=root)
            except FileNotFoundError:
                pass
        return True
    finally:
        os.close(root)


if __name__ == "__main__":
    data = sys.stdin.buffer.read(4097)
    if len(data) > 4096:
        raise ValueError("PR snapshot exceeds its maximum size")
    print("updated" if publish(sys.argv[1], sys.argv[2], json.loads(data)) else "already current")
