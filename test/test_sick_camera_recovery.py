import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAMERA_MODULE_PATH = PROJECT_ROOT / "app" / "CapTrue" / "Camera.py"


class FakeFloatValue:

    def __init__(self):
        self.fCurValue = 0.0


def _module(name, **attributes):
    module = ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    return module


def _install_package(monkeypatch, name):
    parts = name.split(".")
    for index in range(1, len(parts) + 1):
        module_name = ".".join(parts[:index])
        if module_name not in sys.modules:
            module = ModuleType(module_name)
            module.__path__ = []
            monkeypatch.setitem(sys.modules, module_name, module)


def _load_camera_module(monkeypatch, camera_factory):
    monkeypatch.setitem(sys.modules, "CONFIG", _module("CONFIG"))
    monkeypatch.setitem(sys.modules, "Log", _module("Log", logger=Mock()))
    monkeypatch.setitem(
        sys.modules,
        "core",
        _module("core", get_camera_by_sn=camera_factory),
    )

    _install_package(monkeypatch, "harvesters")
    monkeypatch.setitem(
        sys.modules,
        "harvesters.core",
        _module("harvesters.core", Buffer=object, ImageAcquirer=object),
    )

    import_modules = {
        "BKVisionCamera.areascancamera.hikvision.MvImport.CameraParams_const":
        {
            "MV_ACCESS_Exclusive": 1,
            "MV_CAMERALINK_DEVICE": 2,
            "MV_GIGE_DEVICE": 4,
            "MV_USB_DEVICE": 8,
        },
        "BKVisionCamera.areascancamera.hikvision.MvImport.CameraParams_header":
        {
            "MV_CC_DEVICE_INFO": object,
            "MV_CC_DEVICE_INFO_LIST": object,
            "MV_FRAME_OUT_INFO_EX": object,
            "MVCC_FLOATVALUE": FakeFloatValue,
            "MVCC_INTVALUE": object,
        },
        "BKVisionCamera.areascancamera.hikvision.MvImport.MvCameraControl_class":
        {
            "MvCamera": object,
        },
        "BKVisionCamera.areascancamera.hikvision.MvImport.MvErrorDefine_const":
        {
            "MV_E_GC_TIMEOUT": 1,
            "MV_E_NODATA": 2,
            "MV_OK": 0,
        },
    }
    for module_name, attributes in import_modules.items():
        _install_package(monkeypatch, module_name)
        monkeypatch.setitem(sys.modules, module_name,
                            _module(module_name, **attributes))

    module_name = "camera_recovery_test_module"
    spec = importlib.util.spec_from_file_location(module_name,
                                                  CAMERA_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


class FakeNode:

    def __init__(self, value=None):
        self.value = value


class FakeCommand:

    def __init__(self, access_mode="RW"):
        self.access_mode = access_mode
        self.execute_calls = 0

    def execute(self):
        self.execute_calls += 1

    def get_access_mode(self):
        return self.access_mode


class FakeImageAcquirer:

    def __init__(self, start_error=None):
        self.start_error = start_error
        self.start_calls = 0
        self.stop_calls = 0
        self.destroy_calls = 0
        self.device_reset = FakeCommand()
        self.register_streaming_end = FakeCommand()
        self.remote_device = SimpleNamespace(
            node_map=SimpleNamespace(
                DeviceScanType=FakeNode(),
                DeviceReset=self.device_reset,
                DeviceRegistersStreamingEnd=self.register_streaming_end,
                DeviceRegistersStreamingActive=FakeNode(False),
                DeviceRegistersValid=FakeNode(True),
                DeviceTemperature=FakeNode(42.5),
                AcquisitionStart=FakeCommand("RO"),
                AcquisitionStop=FakeCommand("RW"),
                AcquisitionMode=FakeNode("Continuous"),
                TLParamsLocked=FakeNode(1),
            ))

    def start(self):
        self.start_calls += 1
        if self.start_error is not None:
            raise self.start_error

    def stop(self):
        self.stop_calls += 1

    def destroy(self):
        self.destroy_calls += 1


def test_sick_camera_recreates_acquirer_after_partial_start_failure(
        monkeypatch):
    first = FakeImageAcquirer(RuntimeError("AcquisitionStart is not writable"))
    second = FakeImageAcquirer()
    image_acquirers = iter((first, second))
    module = _load_camera_module(monkeypatch,
                                 lambda _sn: next(image_acquirers))
    camera = module.SickCamera("24170059")

    with pytest.raises(RuntimeError, match="AcquisitionStart"):
        camera.open()

    assert camera.camera is None
    assert first.stop_calls == 1
    assert first.destroy_calls == 1

    camera.open()

    assert camera.camera is second
    assert second.start_calls == 1
    assert second.remote_device.node_map.DeviceScanType.value == "Linescan3D"


def test_sick_camera_soft_resets_once_after_repeated_start_lock(monkeypatch):
    start_error = RuntimeError("AcquisitionStart is not writable")
    first = FakeImageAcquirer(start_error)
    second = FakeImageAcquirer(start_error)
    third = FakeImageAcquirer(start_error)
    fourth = FakeImageAcquirer()
    image_acquirers = iter((first, second, third, fourth))
    module = _load_camera_module(monkeypatch,
                                 lambda _sn: next(image_acquirers))
    camera = module.SickCamera("24170059")

    for _ in range(module.SICK_DEVICE_RESET_AFTER_LOCK_FAILURES):
        with pytest.raises(RuntimeError, match="AcquisitionStart"):
            camera.open()

    assert first.device_reset.execute_calls == 0
    assert second.device_reset.execute_calls == 0
    assert third.device_reset.execute_calls == 1
    assert camera._device_reset_attempted is True

    camera.open()

    assert camera.camera is fourth
    assert camera._consecutive_start_failures == 0
    assert camera._device_reset_attempted is False


def test_sick_camera_ends_stale_register_streaming_before_reconnect(
        monkeypatch):
    first = FakeImageAcquirer(RuntimeError("AcquisitionStart is not writable"))
    first.remote_device.node_map.DeviceRegistersStreamingActive.value = True
    second = FakeImageAcquirer()
    image_acquirers = iter((first, second))
    module = _load_camera_module(monkeypatch,
                                 lambda _sn: next(image_acquirers))
    camera = module.SickCamera("24170059")

    with pytest.raises(RuntimeError, match="AcquisitionStart"):
        camera.open()

    assert first.register_streaming_end.execute_calls == 1


def test_sick_camera_reports_status_and_manual_reconnect(monkeypatch):
    first = FakeImageAcquirer()
    module = _load_camera_module(monkeypatch, lambda _sn: first)
    camera = module.SickCamera("24170059")

    camera.open()
    connected = camera.get_status()
    reconnect = camera.request_reconnect()

    assert connected["ok"] is True
    assert connected["connected"] is True
    assert connected["lastAction"] == "acquiring"
    assert connected["temperatureAvailable"] is True
    assert connected["temperatureCelsius"] == 42.5
    assert connected["temperatureSource"] == "DeviceTemperature"
    assert reconnect["ok"] is True
    assert reconnect["action"] == "reconnect3D"
    assert reconnect["queued"] is True
    assert reconnect["camera"]["connected"] is True
    with pytest.raises(RuntimeError, match="manual reconnect"):
        camera.process_pending_actions()
    assert camera.get_status()["connected"] is False
    assert first.stop_calls == 1
    assert first.destroy_calls == 1


def test_sick_camera_manual_device_reset_executes_once(monkeypatch):
    first = FakeImageAcquirer()
    module = _load_camera_module(monkeypatch, lambda _sn: first)
    camera = module.SickCamera("24170059")

    result = camera.request_device_reset()

    assert result["ok"] is True
    assert result["action"] == "reset3D"
    assert result["queued"] is True
    assert result["camera"]["connected"] is True
    with pytest.raises(RuntimeError, match="manual device reset"):
        camera.process_pending_actions()
    status = camera.get_status()
    assert status["connected"] is False
    assert status["deviceResetAttempted"] is True
    assert first.device_reset.execute_calls == 1
    assert first.destroy_calls == 1


def test_sick_camera_fetch_is_bounded_and_timeout_means_no_frame(monkeypatch):
    first = FakeImageAcquirer()
    module = _load_camera_module(monkeypatch, lambda _sn: first)
    camera = module.SickCamera("24170059")
    seen = {}

    class TimeoutException(Exception):
        pass

    def fetch(*, timeout):
        seen["timeout"] = timeout
        raise TimeoutException("no trigger")

    first.fetch = fetch

    assert camera.get_buffer() is None
    assert seen["timeout"] == module.SICK_FETCH_TIMEOUT_SECONDS


def test_sick_camera_release_destroys_acquirer_once(monkeypatch):
    first = FakeImageAcquirer()
    module = _load_camera_module(monkeypatch, lambda _sn: first)
    camera = module.SickCamera("24170059")

    camera.open()
    camera.release()
    camera.release()

    assert camera.camera is None
    assert first.stop_calls == 1
    assert first.destroy_calls == 1


def test_sick_camera_release_still_destroys_when_remote_state_is_broken(
        monkeypatch):
    first = FakeImageAcquirer()
    module = _load_camera_module(monkeypatch, lambda _sn: first)
    camera = module.SickCamera("24170059")

    class BrokenRemoteDevice:

        @property
        def node_map(self):
            raise RuntimeError("transport already disconnected")

    first.remote_device = BrokenRemoteDevice()
    camera.release()

    assert camera.camera is None
    assert first.stop_calls == 1
    assert first.destroy_calls == 1


def test_sick_camera_status_does_not_wait_for_sdk_action(monkeypatch):
    first = FakeImageAcquirer()
    module = _load_camera_module(monkeypatch, lambda _sn: first)
    camera = module.SickCamera("24170059")

    class BusyLock:

        def acquire(self, blocking=True):
            assert blocking is False
            return False

        def release(self):
            raise AssertionError("unacquired lock must not be released")

    camera._camera_lock = BusyLock()
    camera._last_acquiring = True

    status = camera.get_status()

    assert status["connected"] is True
    assert status["acquiring"] is True


def test_hikvision_stop_never_waits_for_blocked_sdk_lock(monkeypatch):
    module = _load_camera_module(monkeypatch, lambda _sn: FakeImageAcquirer())
    camera = module.DaHengCamera(None)

    class BlockedLock:

        def acquire(self, *args, **kwargs):
            raise AssertionError("stop must not acquire the SDK lock")

    camera._sdk_lock = BlockedLock()

    camera.stop()

    assert camera.running is False
    assert camera.state == "stopping"


def test_native_sdk_monitor_marks_only_overdue_call_as_stalled(monkeypatch):
    module = _load_camera_module(monkeypatch, lambda _sn: FakeImageAcquirer())
    now = [10.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: now[0])
    monitor = module.NativeCallMonitor()

    with monitor.track("fetch", 2.0):
        assert monitor.status()["stalled"] is False
        now[0] = 12.1
        status = monitor.status()
        assert status["name"] == "fetch"
        assert status["stalled"] is True

    assert monitor.status()["active"] is False


def test_hikvision_camera_reads_device_temperature(monkeypatch):
    module = _load_camera_module(monkeypatch, lambda _sn: FakeImageAcquirer())

    class FakeHikCamera:

        def MV_CC_GetFloatValue(self, key, value):
            if key == "DeviceTemperature":
                value.fCurValue = 47.25
                return module.MV_OK
            return 1

    temperature, source, error = (
        module.DaHengCamera._read_temperature_from_camera(FakeHikCamera()))

    assert temperature == 47.25
    assert source == "DeviceTemperature"
    assert error == ""


def test_hikvision_camera_reads_live_exposure_and_gain(monkeypatch):
    module = _load_camera_module(monkeypatch, lambda _sn: FakeImageAcquirer())

    class FakeHikCamera:

        def MV_CC_GetFloatValue(self, key, value):
            values = {
                "ExposureTime": 350.0,
                "Gain": 12.0,
            }
            if key not in values:
                return 1
            value.fCurValue = values[key]
            return module.MV_OK

        def MV_CC_GetIntValue(self, key, value):
            raise AssertionError(f"unexpected integer fallback for {key}")

    params, errors = (
        module.DaHengCamera._read_camera_params_from_camera(FakeHikCamera()))

    assert params == {
        "exposureTime": 350.0,
        "gain": 12.0,
    }
    assert errors == {}


def test_hikvision_camera_selects_sensor_for_temperature(monkeypatch):
    module = _load_camera_module(monkeypatch, lambda _sn: FakeImageAcquirer())

    class SelectorRequiredCamera:

        def __init__(self):
            self.sensor_selected = False

        def MV_CC_GetFloatValue(self, key, value):
            if key == "DeviceTemperature" and self.sensor_selected:
                value.fCurValue = 51.5
                return module.MV_OK
            return 0x80000106

        def MV_CC_SetEnumValueByString(self, key, value):
            assert key == "DeviceTemperatureSelector"
            assert value == "Sensor"
            self.sensor_selected = True
            return module.MV_OK

    temperature, source, error = (
        module.DaHengCamera._read_temperature_from_camera(
            SelectorRequiredCamera()))

    assert temperature == 51.5
    assert source == "DeviceTemperature[Sensor]"
    assert error == ""
