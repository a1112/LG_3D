import asyncio
import os
import sys
from pathlib import Path

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
for path in (PROJECT_ROOT, SERVER_ROOT, PROJECT_ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("CONFIG_3D_DIR", str(PROJECT_ROOT / "CONFIG_3D"))
os.environ.setdefault("IMAGE_CACHE_BACKEND", "memory")

from app.Server.api.api_core import app  # noqa: E402


def test_performance_header_is_limited_to_image_routes():
    async def request_paths():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            health_response = await client.get("/health")
            image_response = await client.get("/image/not-found")
        return health_response, image_response

    health_response, image_response = asyncio.run(request_paths())

    assert health_response.status_code == 200
    assert "x-process-time" not in health_response.headers
    assert image_response.status_code == 404
    assert float(image_response.headers["x-process-time"]) >= 0
