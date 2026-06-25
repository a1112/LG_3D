import importlib.util
import json
import sys
import threading
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPTRUE_ROOT = PROJECT_ROOT / "app" / "CapTrue"
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


class FakeSdk:
    def __init__(self, exposure_time=100, gain=5):
        self.exposureTime = exposure_time
        self.gain = gain


class FakeCamera:
    def __init__(self, tmp_path, connected=True):
        self.yaml_config = "Area_Test.yaml"
        self.camera_param_file = tmp_path / "camera_params" / "Area_Test.ini"
        self.capter = SimpleNamespace(sdk=FakeSdk())
        self.connected = connected
        self.last_error = ""
        self.last_frame_time = time.time() - 2
        self.frame_queue = SimpleNamespace(qsize=lambda: 2)
        self._sdk_lock = threading.RLock()
        self.save_count = 0
        self.reconnect_requested = False

    def _save_camera_params(self, capter):
        self.saved_capter = capter
        self.save_count += 1

    def request_reconnect(self):
        self.reconnect_requested = True


def load_camera_control(monkeypatch, tmp_path):
    fake_config = ModuleType("CONFIG")
    fake_config.CONFIG_DIR = tmp_path
    monkeypatch.setitem(sys.modules, "CONFIG", fake_config)
    sys.modules.pop("CameraControl", None)

    spec = importlib.util.spec_from_file_location(
        "CameraControl",
        CAPTRUE_ROOT / "CameraControl.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["CameraControl"] = module
    spec.loader.exec_module(module)
    return module.CameraControl


def make_control(monkeypatch, tmp_path, connected=True):
    (tmp_path / "Area_Test.yaml").write_text(
        "cameraConfig:\n  exposureTime: 321\n  gain: 8\n",
        encoding="utf-8",
    )
    camera = FakeCamera(tmp_path, connected=connected)
    captrue = SimpleNamespace(
        camera_2d=camera,
        cameraInfo=SimpleNamespace(key="Cap_Test", name="Test Camera"),
    )
    return load_camera_control(monkeypatch, tmp_path)(captrue), camera


def test_camera_control_reads_live_status(monkeypatch, tmp_path):
    control, camera = make_control(monkeypatch, tmp_path)

    status = control.get_2d_status()

    assert status["ok"] is True
    assert status["cameraKey"] == "Cap_Test"
    assert status["connected"] is True
    assert status["writable"] is True
    assert status["params"] == {"exposureTime": 100, "gain": 5}
    assert status["source"] == "camera"
    assert status["queueSize"] == 2
    assert status["lastFrameAge"] >= 0
    assert status["paramFile"] == str(camera.camera_param_file)


def test_camera_control_sets_exposure_gain_and_saves(monkeypatch, tmp_path):
    control, camera = make_control(monkeypatch, tmp_path)

    status = control.set_2d_params(exposure_time=450, gain=12, save=True)

    assert camera.capter.sdk.exposureTime == 450
    assert camera.capter.sdk.gain == 12
    assert camera.save_count == 1
    assert camera.saved_capter is camera.capter
    assert status["params"] == {"exposureTime": 450, "gain": 12}


def test_camera_control_refuses_stale_disconnected_capter(monkeypatch, tmp_path):
    control, camera = make_control(monkeypatch, tmp_path, connected=False)
    camera.last_error = "lost connection"

    status = control.get_2d_status()

    assert status["ok"] is False
    assert status["connected"] is False
    assert status["writable"] is False
    assert status["message"] == "lost connection"
    with pytest.raises(RuntimeError, match="not connected"):
        control.set_2d_params(exposure_time=500)


def test_camera_adjustment_api_handles_capture_service_url_edges():
    camera = {"serverIp": "0.0.0.0", "serverPort": 6101}
    assert ApiDataBase._camera_service_base_url(camera) == "http://127.0.0.1:6101"

    missing_port = {"serverIp": "0.0.0.0"}
    assert ApiDataBase._camera_service_base_url(missing_port) is None
    assert ApiDataBase._camera_service_get(missing_port, "/camera/status") == {
        "ok": False,
        "connected": False,
        "message": "相机服务端口未配置",
    }


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def capture_cameras():
    return [
        {
            "key": "Cap_A",
            "name": "A",
            "sn": "001",
            "serverIp": "0.0.0.0",
            "serverPort": 6101,
            "yaml_config": "Area_A.yaml",
        },
        {
            "key": "Cap_B",
            "name": "B",
            "sn": "002",
        },
    ]


def test_camera_adjustment_api_aggregates_capture_service_status(monkeypatch, tmp_path):
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return FakeResponse({
            "ok": True,
            "connected": True,
            "writable": True,
            "params": {
                "exposureTime": 500,
                "gain": 10,
            },
        })

    monkeypatch.setattr(ApiDataBase, "_load_capture_cameras", capture_cameras)
    monkeypatch.setattr(ApiDataBase, "_capture_config_file", lambda: tmp_path / "CapTure.json")
    monkeypatch.setattr(ApiDataBase.requests, "get", fake_get)

    result = ApiDataBase.get_camera_adjustments()

    assert calls == [("http://127.0.0.1:6101/camera/status", ApiDataBase._CAMERA_SERVICE_TIMEOUT)]
    assert result["configFile"] == str(tmp_path / "CapTure.json")
    assert result["cameras"][0]["key"] == "Cap_A"
    assert result["cameras"][0]["serviceUrl"] == "http://127.0.0.1:6101"
    assert result["cameras"][0]["status"]["params"] == {"exposureTime": 500, "gain": 10}
    assert result["cameras"][1]["key"] == "Cap_B"
    assert result["cameras"][1]["serviceUrl"] == ""
    assert result["cameras"][1]["status"]["message"] == "相机服务端口未配置"


def test_camera_adjustment_api_forwards_params_and_reconnect(monkeypatch, tmp_path):
    posts = []

    def fake_post(url, json, timeout):
        posts.append((url, json, timeout))
        return FakeResponse({"ok": True, "path": url.rsplit("/", 2)[-2:]})

    monkeypatch.setattr(ApiDataBase, "_load_capture_cameras", capture_cameras)
    capture_config = tmp_path / "CapTure.json"
    capture_config.write_text(json.dumps({"apiServerIp": "0.0.0.0", "apiServerPort": 6100}), encoding="utf-8")
    monkeypatch.setattr(ApiDataBase, "_capture_config_file", lambda: capture_config)
    monkeypatch.setattr(ApiDataBase.requests, "post", fake_post)

    params = ApiDataBase.CameraAdjustmentPayload(exposureTime=700, gain=13, save=True)
    result = ApiDataBase.set_camera_adjustment("Cap_A", params)
    reconnect = ApiDataBase.reconnect_camera_adjustment("Cap_A")

    assert result["ok"] is True
    assert reconnect["ok"] is True
    assert posts == [
        (
            "http://127.0.0.1:6100/cameras/Cap_A/params",
            {"exposureTime": 700, "gain": 13, "save": True},
            ApiDataBase._CAMERA_SERVICE_TIMEOUT,
        ),
        (
            "http://127.0.0.1:6100/cameras/Cap_A/reconnect",
            {},
            ApiDataBase._CAMERA_SERVICE_TIMEOUT,
        ),
    ]


def test_camera_adjustment_http_routes_forward_to_capture_services(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    posts = []

    def fake_get(url, timeout):
        return FakeResponse({
            "ok": True,
            "connected": True,
            "writable": True,
            "params": {
                "exposureTime": 600,
                "gain": 9,
            },
        })

    def fake_post(url, json, timeout):
        posts.append((url, json, timeout))
        return FakeResponse({"ok": True})

    monkeypatch.setattr(ApiDataBase, "_load_capture_cameras", capture_cameras)
    capture_config = tmp_path / "CapTure.json"
    capture_config.write_text(json.dumps({"apiServerIp": "0.0.0.0", "apiServerPort": 6100}), encoding="utf-8")
    monkeypatch.setattr(ApiDataBase, "_capture_config_file", lambda: capture_config)
    monkeypatch.setattr(ApiDataBase.requests, "get", fake_get)
    monkeypatch.setattr(ApiDataBase.requests, "post", fake_post)

    client = TestClient(ApiDataBase.app)

    status_response = client.get("/camera_adjust")
    params_response = client.post(
        "/camera_adjust/Cap_A",
        json={"exposureTime": 800, "gain": 14, "save": False},
    )
    reconnect_response = client.post("/camera_adjust/Cap_A/reconnect")

    assert status_response.status_code == 200
    assert status_response.json()["cameras"][0]["status"]["params"] == {
        "exposureTime": 600,
        "gain": 9,
    }
    assert params_response.status_code == 200
    assert reconnect_response.status_code == 200
    assert posts == [
        (
            "http://127.0.0.1:6100/cameras/Cap_A/params",
            {"exposureTime": 800, "gain": 14, "save": False},
            ApiDataBase._CAMERA_SERVICE_TIMEOUT,
        ),
        (
            "http://127.0.0.1:6100/cameras/Cap_A/reconnect",
            {},
            ApiDataBase._CAMERA_SERVICE_TIMEOUT,
        ),
    ]


def test_camera_adjustment_settings_ui_is_wired():
    setting_view = (MOTION_STUDIO_ROOT / "qml" / "SettingPage" / "SettingPageView.qml").read_text(
        encoding="utf-8",
    )
    api_qml = (MOTION_STUDIO_ROOT / "qml" / "Api" / "Api_DataBase.qml").read_text(encoding="utf-8")
    camera_qml = (
        MOTION_STUDIO_ROOT / "qml" / "SettingPage" / "CameraSetting" / "CameraSetting.qml"
    ).read_text(encoding="utf-8")
    qrc = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")

    assert 'import "CameraSetting"' in setting_view
    assert 'qsTr("相机调整")' in setting_view
    assert "CameraSetting {}" in setting_view
    assert "qml/SettingPage/CameraSetting/CameraSetting.qml" in qrc
    assert "function getCameraAdjustments" in api_qml
    assert "function setCameraAdjustment" in api_qml
    assert "function reconnectCameraAdjustment" in api_qml
    assert "app.api.getCameraAdjustments" in camera_qml
    assert "app.api.setCameraAdjustment" in camera_qml
    assert "exposureTime: paramValue" in camera_qml
    assert "gain: paramValue" in camera_qml
    assert 'qsTr("曝光时间")' in camera_qml
    assert 'qsTr("增益")' in camera_qml
    assert 'qsTr("在线")' in camera_qml
    assert 'qsTr("离线")' in camera_qml
