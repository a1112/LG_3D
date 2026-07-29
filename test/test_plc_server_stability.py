import logging
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import pytest
from fastapi.testclient import TestClient

from app.plcServer import server, watchdog
from app.plcServer.logging_utils import DroppingQueueHandler


class FakeResult:
    def __init__(self, *, success=True, content=None, message="", error_code=0):
        self.IsSuccess = success
        self.Content = content
        self.Message = message
        self.ErrorCode = error_code


class FakeClient:
    def __init__(self, read_results=None, connect_result=None):
        self.connectTimeOut = None
        self.receiveTimeOut = None
        self.read_results = list(read_results or [])
        self.connect_result = connect_result or FakeResult()
        self.connect_calls = 0
        self.close_calls = 0
        self.write_calls = []

    def ConnectServer(self):
        self.connect_calls += 1
        return self.connect_result

    def ConnectClose(self):
        self.close_calls += 1
        return FakeResult()

    def Read(self, addr, length):
        if self.read_results:
            return self.read_results.pop(0)
        return FakeResult(content=b"\x00" * length)

    def WriteInt16(self, addr, value):
        self.write_calls.append(("int", addr, value))
        return FakeResult()

    def WriteUInt16(self, addr, value):
        self.write_calls.append(("word", addr, value))
        return FakeResult()

    def WriteFloat(self, addr, value):
        self.write_calls.append(("real", addr, value))
        return FakeResult()

    def WriteBool(self, addr, value):
        self.write_calls.append(("bool", addr, value))
        return FakeResult()


def manager_for_clients(
    clients,
    *,
    lock_timeout_seconds=1.0,
    stuck_threshold_seconds=20.0,
):
    remaining = list(clients)

    def factory(_ip, _rack, _slot):
        return remaining.pop(0)

    return server.PLCConnectionManager(
        factory,
        plc_ip="127.0.0.1",
        rack=0,
        slot=0,
        connect_timeout_ms=123,
        receive_timeout_ms=456,
        lock_timeout_seconds=lock_timeout_seconds,
        stuck_threshold_seconds=stuck_threshold_seconds,
    )


def test_sdk_failure_is_checked_and_read_reconnects_once():
    first = FakeClient([FakeResult(success=False, message="cable unplugged", error_code=7)])
    second = FakeClient([FakeResult(content=b"\x00\x2a")])
    manager = manager_for_clients([first, second])

    assert manager.read("DB1", 2) == b"\x00\x2a"
    assert first.close_calls == 1
    assert second.connect_calls == 1
    assert second.connectTimeOut == 123
    assert second.receiveTimeOut == 456
    assert manager.status()["active_operation"] is None


def test_unexpected_factory_failure_is_normalized_for_offline_startup():
    def failing_factory(_ip, _rack, _slot):
        raise OSError("SDK could not load adapter")

    manager = server.PLCConnectionManager(
        failing_factory,
        plc_ip="127.0.0.1",
        rack=0,
        slot=0,
        lock_timeout_seconds=0.1,
    )

    with pytest.raises(server.PLCOperationError, match="SDK could not load adapter"):
        manager.connect()
    assert "SDK could not load adapter" in manager.status()["last_error"]


def test_malformed_success_result_does_not_escape_as_none_content():
    clients = [FakeClient([FakeResult(content=None)]), FakeClient([FakeResult(content=None)])]
    manager = manager_for_clients(clients)

    with pytest.raises(server.PLCUnavailableError, match="invalid content"):
        manager.read("DB1", 2)

    assert all(client.close_calls == 1 for client in clients)


def test_short_sdk_payload_is_failure_and_reconnects():
    clients = [
        FakeClient([FakeResult(content=b"\x00")]),
        FakeClient([FakeResult(content=b"\x00")]),
    ]
    manager = manager_for_clients(clients)

    with pytest.raises(server.PLCUnavailableError, match="returned 1 bytes; expected 2"):
        manager.read("DB1", 2)

    assert all(client.close_calls == 1 for client in clients)


def test_reads_are_serialized_around_non_thread_safe_sdk():
    state_lock = threading.Lock()

    class ConcurrentClient(FakeClient):
        active = 0
        max_active = 0

        def Read(self, _addr, length):
            with state_lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(0.005)
            with state_lock:
                self.active -= 1
            return FakeResult(content=b"\x00" * length)

    client = ConcurrentClient()
    manager = manager_for_clients([client], lock_timeout_seconds=2.0)

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(lambda _: manager.read("DB1", 2), range(24)))

    assert results == [b"\x00\x00"] * 24
    assert client.max_active == 1
    assert client.connect_calls == 1


def test_busy_sdk_does_not_block_health_and_waiters_are_bounded():
    entered = threading.Event()
    release = threading.Event()

    class BlockingClient(FakeClient):
        def Read(self, _addr, length):
            entered.set()
            release.wait(timeout=2)
            return FakeResult(content=b"\x00" * length)

    manager = manager_for_clients(
        [BlockingClient()],
        lock_timeout_seconds=0.05,
        stuck_threshold_seconds=0.1,
    )
    worker = threading.Thread(target=manager.read, args=("DB1", 2))
    worker.start()
    assert entered.wait(timeout=1)

    started = time.monotonic()
    status = manager.status()
    elapsed = time.monotonic() - started
    assert status["service"] == "ok"
    assert status["plc_busy"] is True
    assert status["active_operation"] == "PLC read DB1"
    assert status["operation_age_seconds"] is not None
    assert status["stuck"] is False
    assert elapsed < 0.02

    with pytest.raises(server.PLCBusyError, match="operation queue"):
        manager.read("DB1", 2)

    release.set()
    worker.join(timeout=1)
    assert not worker.is_alive()
    recovered_status = manager.status()
    assert recovered_status["service"] == "ok"
    assert recovered_status["stuck"] is False
    assert recovered_status["active_operation"] is None


def test_stuck_operation_marks_service_unhealthy_for_external_watchdog():
    entered = threading.Event()
    release = threading.Event()

    class BlockingClient(FakeClient):
        def Read(self, _addr, length):
            entered.set()
            release.wait(timeout=2)
            return FakeResult(content=b"\x00" * length)

    manager = manager_for_clients(
        [BlockingClient()],
        lock_timeout_seconds=0.05,
        stuck_threshold_seconds=0.1,
    )
    worker = threading.Thread(target=manager.read, args=("DB1", 2))
    worker.start()
    assert entered.wait(timeout=1)
    time.sleep(0.12)

    status = manager.status()
    assert status["service"] == "unhealthy"
    assert status["stuck"] is True
    assert status["active_operation"] == "PLC read DB1"
    assert status["operation_age_seconds"] >= 0.1

    release.set()
    worker.join(timeout=1)
    assert not worker.is_alive()


def test_write_uses_width_correct_sdk_types_instead_of_write_double():
    client = FakeClient()
    manager = manager_for_clients([client])

    manager.write("DB1", "int", -12)
    manager.write("DB2", "word", 65535)
    manager.write("DB3", "real", "1.25")
    manager.write("M1.0", "bool", 1)

    assert client.write_calls == [
        ("int", "DB1", -12),
        ("word", "DB2", 65535),
        ("real", "DB3", 1.25),
        ("bool", "M1.0", True),
    ]


@pytest.mark.parametrize(
    ("type_str", "value"),
    [
        ("int", 32768),
        ("word", -1),
        ("real", "not-a-number"),
        ("real", float("nan")),
        ("bool", "false"),
        ("dword", 1),
    ],
)
def test_invalid_write_values_fail_before_opening_socket(type_str, value):
    client = FakeClient()
    manager = manager_for_clients([client])

    with pytest.raises(server.PLCConfigurationError):
        manager.write("DB1", type_str, value)

    assert client.connect_calls == 0


def test_value_decoding_and_minimum_length_validation():
    assert server.get_value(struct.pack(">h", -17), "int") == -17
    assert server.get_value(struct.pack(">f", 2.5), "real") == pytest.approx(2.5)
    assert server.get_value(struct.pack(">I", 4_000_000_000), "dword") == 4_000_000_000
    assert server.get_value(b"hello\x00", "string") == "hello"
    assert server.get_value(b"\x80\x00", "word") == 32768
    assert server.get_value(b"\x01", "bool") is True

    with pytest.raises(server.PLCConfigurationError, match="at least 4 bytes"):
        server._validate_read_request("DB1", "real", 2)
    with pytest.raises(server.PLCOperationError, match="non-byte"):
        server.get_value(None, "int")
    with pytest.raises(server.PLCConfigurationError, match="must be integers"):
        server._validate_target("192.0.2.1", "rack", 0)


def test_close_releases_persistent_sdk_session():
    client = FakeClient([FakeResult(content=b"\x00\x01")])
    manager = manager_for_clients([client])
    manager.read("DB1", 2)

    assert manager.close() is True
    assert client.close_calls == 1
    assert manager.status()["plc_connected"] is False


def test_close_cannot_deadlock_on_vendor_lock_leaked_by_sdk_exception():
    class SocketStub:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    client = FakeClient()
    client.interactiveLock = threading.Lock()
    client.interactiveLock.acquire()
    client.CoreSocket = SocketStub()
    client.isPersistentConn = True
    socket = client.CoreSocket

    started = time.monotonic()
    server.PLCConnectionManager._safe_close(client)

    assert time.monotonic() - started < 0.02
    assert socket.closed is True
    assert client.CoreSocket is None
    assert client.isPersistentConn is False
    assert client.close_calls == 0


def test_failed_vendor_close_result_still_forces_socket_release():
    class SocketStub:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class FailedCloseClient(FakeClient):
        def ConnectClose(self):
            self.close_calls += 1
            return FakeResult(success=False, message="close rejected")

    client = FailedCloseClient()
    client.CoreSocket = SocketStub()
    socket = client.CoreSocket

    server.PLCConnectionManager._safe_close(client)

    assert client.close_calls == 1
    assert socket.closed is True
    assert client.CoreSocket is None


class FakeApiManager:
    def __init__(self):
        self.target = ("192.0.2.1", 0, 0)
        self.configured = None
        self.closed = False

    def configure(self, plc_ip, rack, slot, *, connect):
        self.configured = (plc_ip, rack, slot, connect)
        self.target = (plc_ip, rack, slot)

    def read(self, _addr, length):
        return b"\x00\x2a"[:length]

    def status(self):
        return {
            "service": "ok",
            "plc_connected": True,
            "plc_busy": False,
            "plc_ip": self.target[0],
            "rack": self.target[1],
            "slot": self.target[2],
            "last_error": None,
            "last_success_at": 1.0,
        }

    def close(self, timeout_seconds=1.0):
        self.closed = True
        return True


def test_fastapi_routes_validate_inputs_and_use_real_connect_path(monkeypatch):
    fake_manager = FakeApiManager()
    monkeypatch.setattr(server, "plc_manager", fake_manager)

    with TestClient(server.app) as client:
        assert client.get("/health").json()["service"] == "ok"
        response = client.get("/plc/connect/10.1.2.3/7/9")
        assert response.status_code == 200
        assert response.json() is True
        assert fake_manager.configured == ("10.1.2.3", 7, 9, True)

        assert client.get("/plc/get/DB1/int/2").json() == 42
        assert client.get("/plc/get/DB1/bytes/2").json() == [0, 42]
        assert client.get("/plc/get/DB1/unknown/2").status_code == 400
        assert client.get("/plc/get/DB1/real/2").status_code == 400

    assert fake_manager.closed is True


def test_health_returns_503_when_manager_reports_stuck(monkeypatch):
    fake_manager = FakeApiManager()
    original_status = fake_manager.status

    def stuck_status():
        status = original_status()
        status.update({"service": "unhealthy", "stuck": True})
        return status

    fake_manager.status = stuck_status
    monkeypatch.setattr(server, "plc_manager", fake_manager)

    with TestClient(server.app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["stuck"] is True


def test_log_queue_drops_instead_of_blocking_when_sink_is_full():
    log_queue = Queue(maxsize=1)
    handler = DroppingQueueHandler(log_queue)
    record = logging.LogRecord("plc-test", logging.INFO, __file__, 1, "test", (), None)

    handler.emit(record)
    started = time.monotonic()
    handler.emit(record)

    assert time.monotonic() - started < 0.02
    assert handler.dropped_records == 1


class FakeHttpResponse:
    def __init__(self, payload, status=200):
        import json

        self.status = status
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        return False

    def read(self):
        return self.payload


def test_watchdog_health_accepts_service_when_plc_itself_is_offline(monkeypatch):
    response = FakeHttpResponse({
        "service": "ok",
        "plc_connected": False,
        "stuck": False,
    })
    monkeypatch.setattr(watchdog, "urlopen", lambda _url, timeout: response)

    assert watchdog.plc_service_healthy("http://plc/health", timeout=0.1) is True


@pytest.mark.parametrize(
    "payload",
    [
        {"service": "unhealthy", "stuck": True},
        {"service": "ok", "stuck": True},
        {"service": "unexpected", "stuck": False},
        [],
    ],
)
def test_watchdog_rejects_stuck_or_malformed_health(monkeypatch, payload):
    response = FakeHttpResponse(payload)
    monkeypatch.setattr(watchdog, "urlopen", lambda _url, timeout: response)

    assert watchdog.plc_service_healthy("http://plc/health", timeout=0.1) is False


def test_watchdog_restart_backoff_is_exponential_and_capped(monkeypatch):
    monkeypatch.setattr(watchdog, "RESTART_DELAY", 5.0)
    monkeypatch.setattr(watchdog, "RESTART_MAX_DELAY", 20.0)

    assert [watchdog.restart_backoff_seconds(value) for value in range(1, 6)] == [
        5.0,
        10.0,
        20.0,
        20.0,
        20.0,
    ]


def test_watchdog_requires_consecutive_failures_before_restart(monkeypatch):
    class FakeProcess:
        pid = 1234

        def poll(self):
            return None

    process = FakeProcess()
    stopped = []
    health_checks = []

    monkeypatch.setattr(watchdog, "start_plc_process", lambda: process)
    monkeypatch.setattr(watchdog, "plc_service_healthy", lambda: health_checks.append(1) or False)
    monkeypatch.setattr(watchdog, "stop_plc_process", lambda value: stopped.append(value))
    monkeypatch.setattr(watchdog, "CHECK_INTERVAL", 0.01)
    monkeypatch.setattr(watchdog, "STARTUP_GRACE", 0.0)
    monkeypatch.setattr(watchdog, "FAILURE_THRESHOLD", 3)
    monkeypatch.setattr(watchdog, "RESTART_DELAY", 7.0)
    monkeypatch.setattr(watchdog, "RESTART_MAX_DELAY", 7.0)
    monkeypatch.setattr(watchdog, "RESTART_STABLE_SECONDS", 1000.0)

    def controlled_sleep(seconds):
        if seconds == 7.0:
            raise KeyboardInterrupt

    monkeypatch.setattr(watchdog.time, "sleep", controlled_sleep)
    watchdog.supervise_plc_process()

    assert len(health_checks) == 3
    assert stopped == [process]


def test_watchdog_stop_escalates_from_terminate_to_kill(monkeypatch):
    class FakeProcess:
        pid = 4321

        def __init__(self):
            self.terminated = 0
            self.killed = 0
            self.wait_calls = 0

        def poll(self):
            return None

        def terminate(self):
            self.terminated += 1

        def kill(self):
            self.killed += 1

        def wait(self, timeout):
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise watchdog.subprocess.TimeoutExpired("plc", timeout)
            return 0

    process = FakeProcess()
    monkeypatch.setattr(watchdog, "STOP_TIMEOUT", 0.1)

    watchdog.stop_plc_process(process)

    assert process.terminated == 1
    assert process.killed == 1
    assert process.wait_calls == 2


def test_plc_watchdog_marks_real_child_to_prevent_recursion(monkeypatch):
    captured = {}

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(watchdog.subprocess, "Popen", fake_popen)

    watchdog.start_plc_process()

    assert captured["kwargs"]["env"]["LG3D_PLC_WATCHDOG_CHILD"] == "1"
    assert captured["command"][-1].endswith("main.py")
