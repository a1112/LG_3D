import asyncio
from pathlib import Path
import sys
import threading


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "package" / "CoilDataBase",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from Base.utils import Backup


def test_backup_image_task_runs_blocking_work_outside_event_loop(monkeypatch,
                                                                 tmp_path):
    event_loop_thread = threading.get_ident()
    worker_threads = []

    def fake_backup(from_id, to_id, save_folder):
        worker_threads.append(threading.get_ident())
        return {
            "copiedFolders": 1,
        }

    monkeypatch.setattr(Backup, "_backup_image_sync", fake_backup)
    result = asyncio.run(Backup.backup_image_task(1, 2, str(tmp_path)))

    assert result == {"copiedFolders": 1}
    assert worker_threads
    assert worker_threads[0] != event_loop_thread


def test_backup_image_task_awaits_async_progress_callback(monkeypatch,
                                                          tmp_path):
    progress = []
    monkeypatch.setattr(
        Backup,
        "_backup_image_sync",
        lambda *args: {"copiedFolders": 0},
    )

    async def progress_callback(value):
        progress.append(value)

    asyncio.run(
        Backup.backup_image_task(
            1,
            2,
            str(tmp_path),
            msg_func=progress_callback,
        ))

    assert progress == [100]


def test_backup_image_task_rejects_empty_ranges(tmp_path):
    try:
        asyncio.run(Backup.backup_image_task(2, 2, str(tmp_path)))
    except ValueError as exc:
        assert "to_id" in str(exc)
    else:
        raise AssertionError("empty backup range must be rejected")


def test_backup_image_task_rejects_oversized_ranges_before_work(
        monkeypatch, tmp_path):
    called = False

    def fake_backup(*args):
        nonlocal called
        called = True

    monkeypatch.setattr(Backup, "BACKUP_IMAGE_MAX_COILS", 2)
    monkeypatch.setattr(Backup, "_backup_image_sync", fake_backup)

    try:
        asyncio.run(Backup.backup_image_task(1, 4, str(tmp_path)))
    except Backup.BackupRangeLimitExceeded as exc:
        assert "2 coils" in str(exc)
    else:
        raise AssertionError("oversized backup range must be rejected")

    assert called is False


def test_cancelled_backup_holds_slot_until_copy_worker_finishes(monkeypatch,
                                                                tmp_path):
    entered = threading.Event()
    release = threading.Event()
    calls = 0

    def blocked_backup(*args):
        nonlocal calls
        calls += 1
        entered.set()
        release.wait(timeout=2)
        return {"copiedFolders": 0}

    async def exercise():
        semaphore = asyncio.Semaphore(1)
        monkeypatch.setattr(Backup, "_backup_semaphore", semaphore)
        monkeypatch.setattr(Backup, "_backup_image_sync", blocked_backup)

        first = asyncio.create_task(
            Backup.backup_image_task(1, 2, str(tmp_path)))
        assert await asyncio.to_thread(entered.wait, 1)
        first.cancel()
        try:
            await first
        except asyncio.CancelledError:
            pass
        assert semaphore.locked()

        second = asyncio.create_task(
            Backup.backup_image_task(2, 3, str(tmp_path)))
        await asyncio.sleep(0.05)
        assert not second.done()
        assert calls == 1

        release.set()
        await asyncio.wait_for(second, timeout=1)
        assert calls == 2
        assert not semaphore.locked()

    try:
        asyncio.run(exercise())
    finally:
        release.set()


def test_backup_admission_has_finite_wait(monkeypatch, tmp_path):

    async def exercise():
        monkeypatch.setattr(Backup, "_backup_semaphore",
                            asyncio.Semaphore(0))
        monkeypatch.setattr(Backup, "BACKUP_IMAGE_ADMISSION_TIMEOUT", 0.02)

        try:
            await Backup.backup_image_task(1, 2, str(tmp_path))
        except Backup.BackupBusyError as exc:
            assert "busy" in str(exc)
        else:
            raise AssertionError("backup waiter must fail after finite timeout")

    asyncio.run(exercise())
