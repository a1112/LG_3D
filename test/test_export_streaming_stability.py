import asyncio
import datetime
import io
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (
        PROJECT_ROOT,
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "Server",
        PROJECT_ROOT / "package" / "CoilDataBase",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from api import ApiBackupServer, ApiCompat  # noqa: E402
from CoilDataBase import Coil as database_coil  # noqa: E402
from fastapi import HTTPException  # noqa: E402


def test_default_report_limits_cover_normal_24h_production_volume():
    assert ApiBackupServer._EXPORT_MAX_COILS == 5000
    assert ApiBackupServer._EXPORT_MAX_DEFECTS == 20000


def test_report_export_slot_is_held_until_stream_cleanup(monkeypatch):

    async def exercise():
        semaphore = asyncio.Semaphore(1)
        monkeypatch.setattr(ApiBackupServer, "_export_semaphore", semaphore)

        first_output = io.BytesIO(b"first")
        first_result = await ApiBackupServer._run_export(
            lambda: (first_output, 5))
        first_response = ApiBackupServer._stream_xlsx(
            first_result[0], first_result[1], "first.xlsx")
        assert semaphore.locked()

        second_output = io.BytesIO(b"second")
        second_task = asyncio.create_task(
            ApiBackupServer._run_export(lambda: (second_output, 6)))
        await asyncio.sleep(0.05)
        assert not second_task.done()

        await first_response.background()
        second_result = await asyncio.wait_for(second_task, timeout=1)
        second_response = ApiBackupServer._stream_xlsx(
            second_result[0], second_result[1], "second.xlsx")
        assert first_output.closed
        assert semaphore.locked()

        await second_response.background()
        assert second_output.closed
        assert not semaphore.locked()

    asyncio.run(exercise())


def test_simple_export_slot_is_held_until_stream_cleanup(monkeypatch):

    async def exercise():
        semaphore = asyncio.Semaphore(1)
        output = io.BytesIO(b"xlsx")
        monkeypatch.setattr(ApiCompat, "_simple_export_semaphore", semaphore)
        monkeypatch.setattr(ApiCompat, "_build_simple_export", lambda: output)

        response = await ApiCompat.export_data_simple()

        assert semaphore.locked()
        assert not output.closed
        await response.background()
        assert output.closed
        assert not semaphore.locked()

    asyncio.run(exercise())


def test_report_export_rejects_unbounded_id_and_time_ranges(monkeypatch):
    monkeypatch.setattr(ApiBackupServer, "_EXPORT_MAX_COILS", 10)
    monkeypatch.setattr(ApiBackupServer, "_EXPORT_MAX_DAYS", 2)

    try:
        ApiBackupServer._validate_export_id_range(1, 11)
    except HTTPException as exc:
        assert exc.status_code == 413
    else:
        raise AssertionError("oversized ID range must be rejected")

    try:
        ApiBackupServer._validate_export_time_range(
            datetime.datetime(2026, 1, 1), datetime.datetime(2026, 1, 4))
    except HTTPException as exc:
        assert exc.status_code == 413
    else:
        raise AssertionError("oversized time range must be rejected")


def test_time_export_rejects_actual_coil_count_before_workbook(monkeypatch):
    export_module = ApiBackupServer.export
    observed = {}

    def fake_query(start_time,
                   end_time,
                   max_count=None,
                   max_defects=None):
        observed["max_count"] = max_count
        observed["max_defects"] = max_defects
        return list(range(max_count + 1))

    def fail_if_workbook_is_allocated(*args, **kwargs):
        raise AssertionError("workbook must not be allocated for an oversized query")

    monkeypatch.setattr(export_module.Coil, "get_all_join_data_by_time",
                        fake_query)
    monkeypatch.setattr(export_module.xlsxwriter, "Workbook",
                        fail_if_workbook_is_allocated)

    with pytest.raises(export_module.ExportLimitExceeded, match="2 coils"):
        export_module.export_data_by_time(
            datetime.datetime(2026, 1, 1),
            datetime.datetime(2026, 1, 2),
            max_coils=2,
        )

    assert observed["max_count"] == 2
    assert observed["max_defects"] == export_module.DEFAULT_MAX_EXPORT_DEFECTS
    response = ApiBackupServer._export_error_response(
        export_module.ExportLimitExceeded(2))
    assert response.status_code == 413


def test_database_time_bound_probes_ids_before_eager_loading(monkeypatch):
    class FakeQuery:

        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def limit(self, count):
            assert count == 3
            return self

        def all(self):
            return [(3,), (2,), (1,)]

    class FakeSession:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def query(self, *args):
            return FakeQuery()

    eager_loaded = False

    def fail_eager_load(session):
        nonlocal eager_loaded
        eager_loaded = True
        raise AssertionError("oversized query must not eager-load relationships")

    monkeypatch.setattr(database_coil, "Session", FakeSession)
    monkeypatch.setattr(database_coil, "get_all_join_query", fail_eager_load)

    with pytest.raises(database_coil.QueryResultLimitExceeded):
        database_coil.get_all_join_data_by_time(
            datetime.datetime(2026, 1, 1),
            datetime.datetime(2026, 1, 2),
            max_count=2,
        )

    assert not eager_loaded


def test_database_id_range_query_is_bounded(monkeypatch):
    observed_limits = []

    class FakeQuery:

        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def limit(self, count):
            observed_limits.append(count)
            return self

        def all(self):
            return [(3,), (2,), (1,)]

    class FakeSession:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def query(self, *args):
            return FakeQuery()

    monkeypatch.setattr(database_coil, "Session", FakeSession)

    with pytest.raises(database_coil.QueryResultLimitExceeded):
        database_coil.get_secondary_coil_ids_by_range(1, 100000,
                                                      max_count=2)

    assert observed_limits == [3]


def test_export_rejects_defect_limit_before_workbook_allocation(monkeypatch):
    export_module = ApiBackupServer.export

    def reject_query(*args, **kwargs):
        raise database_coil.QueryDefectLimitExceeded(2)

    def fail_if_workbook_is_allocated(*args, **kwargs):
        raise AssertionError("workbook must not be allocated for too many defects")

    monkeypatch.setattr(export_module.Coil, "get_all_join_data_by_id",
                        reject_query)
    monkeypatch.setattr(export_module.xlsxwriter, "Workbook",
                        fail_if_workbook_is_allocated)

    with pytest.raises(export_module.ExportDefectLimitExceeded,
                       match="2 defects"):
        export_module.export_data_by_coil_id(1, 2, max_defects=2)


def test_database_defect_bound_probes_before_eager_loading(monkeypatch):
    observed_limits = []

    class FakeQuery:

        def filter(self, *args):
            return self

        def limit(self, count):
            observed_limits.append(count)
            return self

        def all(self):
            return [(1,), (2,), (3,)]

    class FakeSession:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def query(self, *args):
            return FakeQuery()

    def fail_eager_load(session):
        raise AssertionError("oversized defects must not eager-load relations")

    monkeypatch.setattr(database_coil, "Session", FakeSession)
    monkeypatch.setattr(database_coil, "get_all_join_query", fail_eager_load)

    with pytest.raises(database_coil.QueryDefectLimitExceeded):
        database_coil.get_all_join_data_by_time(
            datetime.datetime(2026, 1, 1),
            datetime.datetime(2026, 1, 2),
            max_count=10,
            max_defects=2,
        )

    assert observed_limits == [3]


def test_report_export_admission_has_finite_wait(monkeypatch):

    async def exercise():
        semaphore = asyncio.Semaphore(0)
        monkeypatch.setattr(ApiBackupServer, "_export_semaphore", semaphore)
        monkeypatch.setattr(ApiBackupServer, "_EXPORT_ADMISSION_TIMEOUT", 0.02)

        with pytest.raises(HTTPException) as exc_info:
            await ApiBackupServer._run_export(
                lambda: (_ for _ in ()).throw(
                    AssertionError("blocked export must not start")))
        assert exc_info.value.status_code == 503

    asyncio.run(exercise())


def test_simple_export_admission_has_finite_wait(monkeypatch):

    async def exercise():
        semaphore = asyncio.Semaphore(0)
        monkeypatch.setattr(ApiCompat, "_simple_export_semaphore", semaphore)
        monkeypatch.setattr(ApiCompat, "_SIMPLE_EXPORT_ADMISSION_TIMEOUT", 0.02)

        response = await ApiCompat.export_data_simple()
        assert response.status_code == 503

    asyncio.run(exercise())
