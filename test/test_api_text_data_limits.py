import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
for path in (PROJECT_ROOT, SERVER_ROOT, PROJECT_ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from CoilDataBase import Coil  # noqa: E402
from api import ApiDataBase  # noqa: E402


class _FakeQuery:

    def __init__(self, rows):
        self.rows = list(rows)
        self.limit_value = None

    def limit(self, value):
        self.limit_value = value
        return self

    def all(self):
        if self.limit_value is None:
            return list(self.rows)
        return list(self.rows[:self.limit_value])


def test_limited_query_probes_one_extra_row_before_returning_results():
    query = _FakeQuery(range(5))

    assert Coil._limited_query_all(query, 5) == list(range(5))
    assert query.limit_value == 6

    oversized = _FakeQuery(range(6))
    with pytest.raises(Coil.QueryResultLimitExceeded):
        Coil._limited_query_all(oversized, 5)
    assert oversized.limit_value == 6


@pytest.mark.parametrize("endpoint_name,repository_name", [
    ("get_point_data", "get_point_data"),
    ("get_line_data", "get_line_data"),
])
def test_text_data_endpoints_map_oversized_queries_to_413(
        monkeypatch, endpoint_name, repository_name):
    seen = {}

    def fail_query(coil_id, surface_key, max_count=None):
        seen.update(coil_id=coil_id,
                    surface_key=surface_key,
                    max_count=max_count)
        raise Coil.QueryResultLimitExceeded(max_count)

    async def immediate_threadpool(call):
        return call()

    monkeypatch.setattr(Coil, repository_name, fail_query)
    monkeypatch.setattr(ApiDataBase, "run_in_threadpool", immediate_threadpool)

    endpoint = getattr(ApiDataBase, endpoint_name)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(endpoint(42, "S"))

    assert exc_info.value.status_code == 413
    assert seen == {
        "coil_id": 42,
        "surface_key": "S",
        "max_count": ApiDataBase._MAX_TEXT_DATA_RESULTS,
    }
