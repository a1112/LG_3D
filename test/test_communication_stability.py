import importlib.util
import logging
from pathlib import Path
from socket import timeout as SocketTimeout
import sys
import threading
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TCP_SERVER_PATH = PROJECT_ROOT / "app" / "Communication" / "TcpServer.py"
HTTP_SERVER_PATH = PROJECT_ROOT / "app" / "Communication" / "HttpServer.py"


def _load_tcp_server(monkeypatch, decode):
    monkeypatch.setitem(
        sys.modules,
        "HttpServer",
        SimpleNamespace(start_http_server=lambda: None),
    )
    monkeypatch.setitem(sys.modules, "DecodeData", SimpleNamespace(Decode=decode))
    monkeypatch.setitem(
        sys.modules,
        "Log",
        SimpleNamespace(logger=logging.getLogger("test.communication")),
    )
    module_name = "communication_tcp_server_test_module"
    spec = importlib.util.spec_from_file_location(module_name, TCP_SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_http_server(monkeypatch):
    monkeypatch.setitem(sys.modules, "DecodeData", SimpleNamespace(currentCoil={}))
    module_name = "communication_http_server_test_module"
    spec = importlib.util.spec_from_file_location(module_name, HTTP_SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_tcp_client_idle_timeout_closes_socket_and_releases_slot(monkeypatch):
    decoded = []
    module = _load_tcp_server(monkeypatch, decoded.append)

    class FakeSocket:
        def __init__(self):
            self.responses = iter((b"packet", SocketTimeout()))
            self.timeout = None
            self.closed = False

        def settimeout(self, value):
            self.timeout = value

        def recv(self, _size):
            response = next(self.responses)
            if isinstance(response, Exception):
                raise response
            return response

        def close(self):
            self.closed = True

    class FakeSlot:
        def __init__(self):
            self.released = False

        def release(self):
            self.released = True

    client_socket = FakeSocket()
    slot = FakeSlot()
    module.tcplink(client_socket, ("127.0.0.1", 12345), slot)

    assert decoded == [b"packet"]
    assert client_socket.timeout == module.CLIENT_IDLE_TIMEOUT
    assert client_socket.closed is True
    assert slot.released is True


def test_http_server_supervisor_restarts_after_failure(monkeypatch):
    module = _load_http_server(monkeypatch)
    stop_event = threading.Event()
    calls = []

    def fake_run_http_server():
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            raise SystemExit(1)
        stop_event.set()

    monkeypatch.setattr(module, "run_http_server", fake_run_http_server)
    monkeypatch.setattr(module, "HTTP_RESTART_DELAY", 0.01)

    module.supervise_http_server(stop_event)

    assert calls == [1, 2]
