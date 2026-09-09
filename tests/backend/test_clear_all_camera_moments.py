from __future__ import annotations

from pathlib import Path

import pytest
from baby_monitor.database import Database, StorageError
from baby_monitor.models import SleepEventCreate, utc_now


def test_clear_all_camera_moments_removes_files_and_preserves_history(tmp_path: Path) -> None:
    database = Database(tmp_path)
    frame = database.add_frame(b"image", "image/jpeg", utc_now())
    sleep = database.add_sleep_event(SleepEventCreate(started_at=utc_now(), kind="nap", source="manual"))
    image = database.get_frame_path(frame.id)
    assert image is not None

    assert database.clear_all_camera_moments() == {"frames": 1, "bytes": 5}
    assert database.list_frames()[1] == 0
    assert not image.exists()
    assert database.get_sleep_event(sleep.id) is not None


def test_clear_all_camera_moments_allows_missing_file_and_rejects_escape(tmp_path: Path) -> None:
    database = Database(tmp_path)
    frame = database.add_frame(b"image", "image/jpeg", utc_now())
    image = database.get_frame_path(frame.id)
    assert image is not None
    image.unlink()
    with database._connect() as connection:
        connection.execute("UPDATE frames SET relative_path = ? WHERE id = ?", ("../outside.jpg", frame.id))

    with pytest.raises(StorageError, match="escaped"):
        database.clear_all_camera_moments()
    assert database.get_frame(frame.id) is not None


def test_clear_all_camera_moments_removes_preexisting_orphan_files(tmp_path: Path) -> None:
    database = Database(tmp_path)
    orphan = database.frames_dir / "2026" / "orphan.jpg"
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"orphan")

    assert database.clear_all_camera_moments() == {"frames": 0, "bytes": 0}
    assert not orphan.exists()



def test_clear_all_camera_moments_rolls_back_when_deleting_staged_file_fails(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path)
    frame = database.add_frame(b"image", "image/jpeg", utc_now())
    image = database.get_frame_path(frame.id)
    assert image is not None
    original_unlink = Path.unlink

    def fail_unlink(path: Path, missing_ok: bool = False) -> None:
        if any(parent.name == ".clear-all-staging" for parent in path.parents):
            raise OSError("disk full")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    with pytest.raises(StorageError, match="disk full"):
        database.clear_all_camera_moments()
    assert database.get_frame(frame.id) is not None
    assert image.exists()
