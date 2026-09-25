import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
for path in (PROJECT_ROOT, SERVER_ROOT, PROJECT_ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.Server import Server  # noqa: E402


class FakeHealthResponse:

    def __init__(self, payload, status=200):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self._body


def test_image_health_requires_minimum_api_version(monkeypatch):
    payload = {
        "service": "rust_image_service",
        "status": "ok",
        "apiVersion": 1
    }
    monkeypatch.setattr(Server.urllib.request, "urlopen",
                        lambda *args, **kwargs: FakeHealthResponse(payload))

    assert not Server._rust_service_healthy(
        "http://example/health", "rust_image_service", minimum_api_version=2)

    payload["apiVersion"] = "2"
    assert Server._rust_service_healthy("http://example/health",
                                        "rust_image_service",
                                        minimum_api_version=2)


def test_versionless_health_remains_compatible_without_version_requirement(
        monkeypatch):
    payload = {"service": "rust_api_service", "status": "ok"}
    monkeypatch.setattr(Server.urllib.request, "urlopen",
                        lambda *args, **kwargs: FakeHealthResponse(payload))

    assert Server._rust_service_healthy("http://example/health",
                                        "rust_api_service")
    assert not Server._rust_service_healthy(
        "http://example/health", "rust_api_service", minimum_api_version=2)


def test_image_service_startup_checks_required_api_version(monkeypatch):
    seen = {}

    def fake_health(service_url, expected_service, minimum_api_version=None):
        seen.update({
            "service_url": service_url,
            "expected_service": expected_service,
            "minimum_api_version": minimum_api_version,
        })
        return True

    monkeypatch.setattr(Server, "_env_flag", lambda *args, **kwargs: True)
    monkeypatch.setattr(Server, "_rust_service_healthy", fake_health)

    Server._start_rust_image_service()

    assert seen == {
        "service_url": Server.RUST_IMAGE_SERVICE_URL,
        "expected_service": "rust_image_service",
        "minimum_api_version": Server.RUST_IMAGE_SERVICE_MIN_API_VERSION,
    }


def test_find_rust_service_exe_selects_newest_candidate(monkeypatch, tmp_path):
    server_file = tmp_path / "Server.py"
    server_file.write_text("", encoding="utf-8")
    service_dir = tmp_path / "rust_image_service" / "target"
    release_exe = service_dir / "release" / "rust_image_service.exe"
    debug_exe = service_dir / "debug" / "rust_image_service.exe"
    release_exe.parent.mkdir(parents=True)
    debug_exe.parent.mkdir(parents=True)
    release_exe.write_bytes(b"release")
    debug_exe.write_bytes(b"debug")
    os.utime(release_exe, ns=(1_000_000_000, 1_000_000_000))
    os.utime(debug_exe, ns=(2_000_000_000, 2_000_000_000))
    monkeypatch.setattr(Server, "__file__", str(server_file))

    assert Server._find_rust_service_exe("rust_image_service") == debug_exe
