import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOTION_STUDIO_ROOT = PROJECT_ROOT / "app" / "UI" / "MotionStudio"

for path in (
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "Server",
        PROJECT_ROOT / "package" / "CoilDataBase",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from api import ApiDataBase
from api import hardware_monitor


def _address(family, address, netmask="", broadcast=""):
    return SimpleNamespace(
        family=family,
        address=address,
        netmask=netmask,
        broadcast=broadcast,
        ptp="",
    )


def _counters(bytes_sent, bytes_recv):
    return SimpleNamespace(
        bytes_sent=bytes_sent,
        bytes_recv=bytes_recv,
        packets_sent=10,
        packets_recv=20,
        errin=1,
        errout=2,
        dropin=3,
        dropout=4,
    )


def test_network_monitor_reports_link_addresses_and_throughput(monkeypatch):
    stats = {
        "Camera NIC": SimpleNamespace(
            isup=True,
            speed=1000,
            mtu=1500,
            duplex=hardware_monitor.psutil.NIC_DUPLEX_FULL,
        ),
    }
    addresses = {
        "Camera NIC": [
            _address(hardware_monitor.socket.AF_INET, "192.168.100.1"),
            _address(hardware_monitor.psutil.AF_LINK, "AA-BB-CC-DD-EE-FF"),
        ],
    }
    counter_samples = iter(({
        "Camera NIC": _counters(1000, 2000)
    }, {
        "Camera NIC": _counters(3000, 6000)
    }))
    monotonic_samples = iter((10.0, 12.0))

    monkeypatch.setattr(hardware_monitor.psutil, "net_if_stats",
                        lambda: stats)
    monkeypatch.setattr(hardware_monitor.psutil, "net_if_addrs",
                        lambda: addresses)
    monkeypatch.setattr(hardware_monitor.psutil, "net_io_counters",
                        lambda pernic: next(counter_samples))
    monkeypatch.setattr(hardware_monitor.time, "monotonic",
                        lambda: next(monotonic_samples))
    monkeypatch.setattr(hardware_monitor.os, "name", "nt")
    hardware_monitor._LAST_SAMPLES.clear()

    first = hardware_monitor.get_network_adapters()[0]
    second = hardware_monitor.get_network_adapters()[0]

    assert first["name"] == "Camera NIC"
    assert first["isUp"] is True
    assert first["speedMbps"] == 1000
    assert first["ipv4"] == ["192.168.100.1"]
    assert first["mac"] == "AA-BB-CC-DD-EE-FF"
    assert first["rxBytesPerSecond"] == 0
    assert second["rxBytesPerSecond"] == 2000
    assert second["txBytesPerSecond"] == 1000
    assert second["sampleInterval"] == 2
    assert second["errorsIn"] == 1
    assert second["dropsOut"] == 4
    assert second["canControl"] is True


def test_network_monitor_disables_loopback_control(monkeypatch):
    monkeypatch.setattr(
        hardware_monitor.psutil,
        "net_if_stats",
        lambda: {
            "Loopback": SimpleNamespace(
                isup=True,
                speed=0,
                mtu=65536,
                duplex=hardware_monitor.psutil.NIC_DUPLEX_UNKNOWN,
            )
        },
    )
    monkeypatch.setattr(
        hardware_monitor.psutil,
        "net_if_addrs",
        lambda: {
            "Loopback": [
                _address(hardware_monitor.socket.AF_INET, "127.0.0.1")
            ]
        },
    )
    monkeypatch.setattr(
        hardware_monitor.psutil,
        "net_io_counters",
        lambda pernic: {"Loopback": _counters(1, 1)},
    )
    monkeypatch.setattr(hardware_monitor.os, "name", "nt")
    hardware_monitor._LAST_SAMPLES.clear()

    adapter = hardware_monitor.get_network_adapters()[0]

    assert adapter["isLoopback"] is True
    assert adapter["canControl"] is False
    assert "loopback" in adapter["controlReason"]


def test_network_monitor_uses_native_speed_for_fast_windows_link(monkeypatch):
    monkeypatch.setattr(
        hardware_monitor.psutil,
        "net_if_stats",
        lambda: {
            "10G Camera NIC": SimpleNamespace(
                isup=True,
                speed=4294,
                mtu=1500,
                duplex=hardware_monitor.psutil.NIC_DUPLEX_FULL,
            )
        },
    )
    monkeypatch.setattr(hardware_monitor.psutil, "net_if_addrs",
                        lambda: {"10G Camera NIC": []})
    monkeypatch.setattr(
        hardware_monitor.psutil,
        "net_io_counters",
        lambda pernic: {"10G Camera NIC": _counters(1, 1)},
    )
    monkeypatch.setattr(hardware_monitor.os, "name", "nt")
    monkeypatch.setattr(hardware_monitor, "_windows_link_speeds",
                        lambda: {"10G Camera NIC": 10000})
    hardware_monitor._LAST_SAMPLES.clear()

    adapter = hardware_monitor.get_network_adapters()[0]

    assert adapter["speedMbps"] == 10000


def test_network_adapter_control_uses_encoded_powershell(monkeypatch):
    adapter_name = "相机网卡'; Remove-Item C:\\*"
    completed = SimpleNamespace(returncode=0, stdout='{"Status":"Up"}',
                                stderr="")
    scripts = []
    monkeypatch.setattr(hardware_monitor.os, "name", "nt")
    monkeypatch.setattr(hardware_monitor.psutil, "net_if_stats",
                        lambda: {adapter_name: SimpleNamespace(
                            isup=True, speed=1000, mtu=1500,
                            duplex=hardware_monitor.psutil.NIC_DUPLEX_FULL)})
    monkeypatch.setattr(hardware_monitor.psutil, "net_if_addrs",
                        lambda: {adapter_name: []})
    monkeypatch.setattr(hardware_monitor.psutil, "net_io_counters",
                        lambda pernic: {adapter_name: _counters(1, 1)})
    monkeypatch.setattr(hardware_monitor, "_run_powershell",
                        lambda script: scripts.append(script) or completed)
    hardware_monitor._LAST_SAMPLES.clear()

    result = hardware_monitor.control_network_adapter(adapter_name, "restart")

    assert result["ok"] is True
    assert result["adapterName"] == adapter_name
    assert "Restart-NetAdapter" in scripts[0]
    assert adapter_name not in scripts[0]
    with pytest.raises(ValueError, match="unsupported action"):
        hardware_monitor.control_network_adapter(adapter_name, "delete")


def test_service_monitor_reports_port_and_process_services(monkeypatch):
    definitions = (
        {
            "key": "port_service",
            "name": "Port Service",
            "category": "Core",
            "port": 5010,
            "commandTokens": ("server.py",),
        },
        {
            "key": "worker",
            "name": "Worker",
            "category": "Core",
            "commandTokens": ("worker.py",),
        },
    )
    snapshots = {
        10: {
            "pid": 10,
            "processName": "python.exe",
            "commandLine": "python Server.py",
            "commandText": "python server.py",
            "cwd": "D:/app",
            "cwdText": "d:/app",
            "startedAt": 100.0,
            "memoryBytes": 1024,
        },
        20: {
            "pid": 20,
            "processName": "python.exe",
            "commandLine": "python Worker.py",
            "commandText": "python worker.py",
            "cwd": "D:/app",
            "cwdText": "d:/app",
            "startedAt": 200.0,
            "memoryBytes": 2048,
        },
    }
    monkeypatch.setattr(hardware_monitor, "_SERVICE_DEFINITIONS",
                        definitions)
    monkeypatch.setattr(hardware_monitor, "_process_snapshots",
                        lambda: snapshots)
    monkeypatch.setattr(hardware_monitor, "_listening_pids_by_port",
                        lambda: {5010: {10}})
    monkeypatch.setattr(hardware_monitor.time, "time", lambda: 300.0)

    services = hardware_monitor.get_service_statuses()

    assert services[0]["online"] is True
    assert services[0]["port"] == 5010
    assert services[0]["pid"] == 10
    assert services[0]["uptimeSeconds"] == 200
    assert services[1]["online"] is True
    assert services[1]["port"] is None
    assert services[1]["pid"] == 20
    assert services[1]["memoryBytes"] == 2048


def test_hardware_monitor_aggregates_camera_and_network_status(monkeypatch):
    monkeypatch.setattr(
        ApiDataBase,
        "_capture_status_value",
        lambda realtime=False: {
            "ok": False,
            "cameras": [
                {
                    "key": "Cap_A",
                    "serviceReady": True,
                    "cap2D": True,
                    "cap3D": True,
                    "camera2D": {"ok": True},
                    "camera3D": {"ok": True},
                    "lastError2D": "",
                    "lastError3D": "",
                },
                {
                    "key": "Cap_B",
                    "serviceReady": True,
                    "cap2D": True,
                    "cap3D": False,
                    "camera2D": {"ok": False},
                    "lastError2D": "offline",
                    "lastError3D": "",
                },
            ],
        },
    )
    monkeypatch.setattr(
        ApiDataBase,
        "get_network_adapters",
        lambda: [
            {"name": "NIC A", "isUp": True},
            {"name": "NIC B", "isUp": False},
        ],
    )
    monkeypatch.setattr(ApiDataBase, "_capture_service_base_url",
                        lambda: "http://127.0.0.1:6100")
    monkeypatch.setattr(
        ApiDataBase,
        "get_service_statuses",
        lambda: [
            {"key": "service_a", "online": True},
            {"key": "service_b", "online": False},
        ],
    )

    result = ApiDataBase._hardware_monitor_value()

    assert result["ok"] is False
    assert result["captureServiceUrl"] == "http://127.0.0.1:6100"
    assert result["summary"] == {
        "cameraCount": 2,
        "cameraOnline": 1,
        "camera2DCount": 2,
        "camera2DOnline": 1,
        "camera3DCount": 1,
        "camera3DOnline": 1,
        "networkAdapterCount": 2,
        "networkAdapterOnline": 1,
        "serviceCount": 2,
        "serviceOnline": 1,
        "temperatureSensorCount": 0,
        "maxTemperatureCelsius": None,
    }


def test_hardware_monitor_http_routes(monkeypatch):
    from fastapi.testclient import TestClient

    controls = []
    service_restarts = []
    monitor_payload = {
        "ok": True,
        "cameras": [],
        "networkAdapters": [],
        "summary": {
            "cameraCount": 0,
            "cameraOnline": 0,
            "networkAdapterCount": 0,
            "networkAdapterOnline": 0,
        },
    }
    monkeypatch.setattr(ApiDataBase, "_hardware_monitor_value",
                        lambda: monitor_payload)
    monkeypatch.setattr(
        ApiDataBase,
        "control_network_adapter",
        lambda name, action: controls.append((name, action)) or {
            "ok": True,
            "adapterName": name,
            "action": action,
        },
    )
    monkeypatch.setattr(
        ApiDataBase,
        "get_service_statuses",
        lambda: [{"key": "api", "online": True}],
    )
    monkeypatch.setattr(
        ApiDataBase,
        "restart_service",
        lambda key: service_restarts.append(key) or {
            "ok": True,
            "serviceKey": key,
        },
    )
    client = TestClient(ApiDataBase.app)

    status_response = client.get("/hardware_monitor")
    services_response = client.get("/services/status")
    control_response = client.post(
        "/network/adapters/%E7%9B%B8%E6%9C%BA%E7%BD%91%E5%8D%A1/control",
        json={"action": "restart"},
    )
    restart_response = client.post("/services/capture/restart", json={})

    assert status_response.status_code == 200
    assert status_response.json() == monitor_payload
    assert services_response.status_code == 200
    assert services_response.json()["summary"] == {
        "serviceCount": 1,
        "serviceOnline": 1,
    }
    assert restart_response.status_code == 200
    assert restart_response.json()["serviceKey"] == "capture"
    assert service_restarts == ["capture"]
    assert control_response.status_code == 200
    assert control_response.json()["action"] == "restart"
    assert controls == [("相机网卡", "restart")]


def test_camera_dimension_controls_are_proxied_to_capture_service(monkeypatch):
    posts = []

    class FakeResponse:

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    monkeypatch.setattr(ApiDataBase, "_capture_service_base_url",
                        lambda: "http://127.0.0.1:6100")
    monkeypatch.setattr(ApiDataBase, "_legacy_camera_service_base_url",
                        lambda camera: None)
    monkeypatch.setattr(
        ApiDataBase.requests,
        "post",
        lambda url, json, timeout: posts.append(url) or FakeResponse(),
    )
    camera = {"key": "Cap_A"}

    ApiDataBase._camera_service_post(camera, "/camera/reconnect/2d")
    ApiDataBase._camera_service_post(camera, "/camera/reconnect/3d")
    ApiDataBase._camera_service_post(camera, "/camera/reset/3d")

    assert posts == [
        "http://127.0.0.1:6100/cameras/Cap_A/reconnect/2d",
        "http://127.0.0.1:6100/cameras/Cap_A/reconnect/3d",
        "http://127.0.0.1:6100/cameras/Cap_A/reset/3d",
    ]


def test_capture_service_exposes_dimension_controls(monkeypatch):
    from fastapi.testclient import TestClient

    module_path = PROJECT_ROOT / "app" / "CapTrue" / "Server.py"
    spec = importlib.util.spec_from_file_location(
        "capture_server_hardware_monitor_test",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    calls = []
    camera_control = SimpleNamespace(
        reconnect_2d=lambda: calls.append("2d") or {"ok": True})
    cap = SimpleNamespace(
        cameraControl=camera_control,
        reconnect_3d=lambda: calls.append("3d") or {"ok": True},
        reset_3d=lambda: calls.append("reset3d") or {"ok": True},
        get_capture_status=lambda: {
            "key": "Cap_A",
            "serviceReady": True,
            "cap2D": True,
            "cap3D": True,
            "camera2D": {"ok": True},
            "camera3D": {"ok": True},
            "lastError3D": "",
        },
        getCreatedFile=lambda clear=False: [],
    )
    capture_config = SimpleNamespace(
        config_file="CapTure.json",
        apiServerIp="127.0.0.1",
        apiServerPort=6100,
    )
    captured_app = {}
    monkeypatch.setattr(
        module.uvicorn,
        "run",
        lambda app, **kwargs: captured_app.setdefault("app", app),
    )
    module.CaptureApiServer(capture_config, {"Cap_A": cap}).run()
    client = TestClient(captured_app["app"])

    assert client.post("/cameras/Cap_A/reconnect/2d").status_code == 200
    assert client.post("/cameras/Cap_A/reconnect/3d").status_code == 200
    assert client.post("/cameras/Cap_A/reset/3d").status_code == 200
    assert calls == ["2d", "3d", "reset3d"]


def test_hardware_monitor_qml_popup_is_wired():
    api_qml = (
        MOTION_STUDIO_ROOT / "qml" / "Api" / "Api_DataBase.qml"
    ).read_text(encoding="utf-8")
    popup_qml = (
        MOTION_STUDIO_ROOT / "qml" / "PopupView" / "HardwareMonitor"
        / "HardwareMonitorView.qml"
    ).read_text(encoding="utf-8")
    pops_qml = (
        MOTION_STUDIO_ROOT / "qml" / "PopupView" / "Pops.qml"
    ).read_text(encoding="utf-8")
    header_qml = (
        MOTION_STUDIO_ROOT / "qml" / "Pages" / "Header" / "TopTools.qml"
    ).read_text(encoding="utf-8")
    qrc = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")

    assert "function getHardwareMonitor" in api_qml
    assert "function reconnectCamera2D" in api_qml
    assert "function reconnectCamera3D" in api_qml
    assert "function resetCamera3D" in api_qml
    assert "function controlNetworkAdapter" in api_qml
    assert "interval: 1000" in popup_qml
    assert "app.api.getHardwareMonitor" in popup_qml
    assert 'text: "总览"' in popup_qml
    assert 'text: "3D 相机  "' in popup_qml
    assert 'text: "2D 相机  "' in popup_qml
    assert 'text: "网卡  "' in popup_qml
    assert 'text: "服务  "' in popup_qml
    assert "serviceModel" in popup_qml
    assert "temperatureCelsius" in popup_qml
    assert "camera2DOnline" in popup_qml
    assert "camera3DOnline" in popup_qml
    assert "confirmNetworkAction" in popup_qml
    assert "confirmCameraReset" in popup_qml
    assert "HardwareMonitorView{id:hardwareMonitorView}" in pops_qml
    assert "popupHardwareMonitorView" in pops_qml
    assert "popManage.popupHardwareMonitorView()" in header_qml
    assert "qml/PopupView/HardwareMonitor/HardwareMonitorView.qml" in qrc
