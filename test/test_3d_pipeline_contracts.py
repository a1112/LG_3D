"""Offline checks for calibrated 3D data and defect-coordinate contracts."""
import datetime
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "app", ROOT / "app/Base", ROOT / "app/algorithm_runtime"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from Base.alg import detection
from Base.property.Base import DataIntegration, DataIntegrationList
from Base.property.Types import DetectionType
from Base.property.ServerConfigProperty import SurfaceConfigProperty


def integration(tmp_path):
    data = DataIntegration("123", tmp_path, "L", "S")
    data.npy_mask = np.full((8, 10), 255, dtype=np.uint8)
    data._circleConfig_ = {"inner_circle": {"circlex": [5, 4, 1]}}
    data.scan3dCoordinateScaleX = 0.5
    data.scan3dCoordinateScaleY = 0.8
    data.scan3dCoordinateScaleZ = 0.25
    data.scan3dCoordinateOffsetZ = 3000.0
    return data


def test_depth_sanitization_keeps_input_and_median_finite(tmp_path):
    data = integration(tmp_path)
    depth = np.full((8, 10), 100.0)
    depth[0, :4] = [np.nan, np.inf, -1, 0]
    data.npy_mask[1, 0] = 0
    depth[1, 0] = 99999
    data.set_npy_data(depth)
    assert np.isnan(depth[0, 0])
    assert np.isfinite(data.npy_data).all()
    assert data.npy_data[1, 0] == 0
    assert data.median_non_zero == 100
    assert data.median_3d_mm == 3025


def test_integer_line_conversion_preserves_fractional_millimetres(tmp_path):
    data = integration(tmp_path)
    points = np.array([[1, 2, 101]], dtype=np.uint16)
    converted = data.point_to_mm(points)
    assert converted[0, 2] == 3025.25
    assert points[0, 2] == 101


def test_integration_list_restarts_after_partial_or_nested_iteration(tmp_path):
    first = integration(tmp_path)
    second = integration(tmp_path)
    first.set_npy_data(np.ones((8, 10)))
    second.set_npy_data(np.ones((8, 10)))
    items = DataIntegrationList()
    assert not items
    items.append(first)
    items.append(second)
    iterator = iter(items)
    assert next(iterator) is first
    assert list(items) == [first, second]
    assert next(iterator) is second
    assert [(a, b) for a in items for b in items] == [
        (first, first), (first, second), (second, first), (second, second)]


def test_commit_does_not_mutate_datetime_for_retry(tmp_path, monkeypatch):
    import Base.property.Base as base
    data = integration(tmp_path)
    saved = []
    monkeypatch.setattr(base, "addCoilState", saved.append)
    data.commit()
    data.commit()
    assert len(saved) == 2
    assert isinstance(data.dictData["startTime"], datetime.datetime)


@pytest.mark.parametrize("mode,box", [
    (DetectionType.Detection, [10, 20, 30, 40, 1, 0.9, "scratch"]),
    (DetectionType.DetectionAndClassifiers, [210, 120, 230, 140, 1, 0.9, "scratch"]),
])
def test_detection_coordinates_apply_tile_origin_exactly_once(tmp_path, monkeypatch, mode, box):
    saved = []
    monkeypatch.setattr(detection.control, "detection_model", mode)
    monkeypatch.setattr(detection, "detection_by_image", lambda *a, **k: (
        [[box]], [None], [(200, 100, 300, 300)]))
    monkeypatch.setattr(detection, "add_defects", saved.extend)
    data = integration(tmp_path)
    data.npy_image = np.zeros((500, 600), dtype=np.uint8)
    detection.detection(data)
    assert (saved[0]["defectX"], saved[0]["defectY"], saved[0]["defectW"], saved[0]["defectH"]) == (210, 120, 20, 20)
    assert data.defect_dict["scratch"] == [(210, 120, 230, 140, 1, 0.9)]


def test_classified_xml_boxes_are_local_while_returned_boxes_stay_global(monkeypatch):
    monkeypatch.setattr(detection.control, "detection_model", DetectionType.DetectionAndClassifiers)
    monkeypatch.setattr(detection.control, "save_detection", True)
    monkeypatch.setattr(detection.control, "save_sub_image", False)
    monkeypatch.setattr(detection, "get_clip_images", lambda *a, **k: ([None], [None], [(100, 200, 300, 300)]))
    monkeypatch.setattr(detection, "classifiers_data", lambda *a, **k: ([], []))
    captured = []
    monkeypatch.setattr(detection, "save_detection", lambda results, *a, **k: captured.extend(results))
    model = SimpleNamespace(predict=lambda images: [[[110, 220, 130, 240, 1, 0.9, "scratch"]]])
    results, _, _ = detection.detection_by_image(np.zeros((600, 600), dtype=np.uint8), np.ones((600, 600)), cdm_=model)
    assert captured[0][0][:4] == [10, 20, 30, 40]
    assert results[0][0][:4] == [110, 220, 130, 240]


def test_mesh_lookup_falls_back_to_obj_without_balsam(tmp_path):
    config = object.__new__(SurfaceConfigProperty)
    config.saveFolder = tmp_path
    folder = tmp_path / "123"
    folder.mkdir()
    obj = folder / "3D.obj"
    obj.write_text("v 0 0 0\n", encoding="ascii")
    assert Path(config.get_mesh_file(123)) == obj
    native = folder / "meshes/defaultobject_mesh.mesh"
    native.parent.mkdir()
    native.write_bytes(b"mesh")
    assert Path(config.get_mesh_file(123)) == native


@pytest.mark.parametrize("shape,parts", [((601, 803), 3), ((80, 90), 7)])
def test_detection_tiles_cover_remainder_and_small_images(shape, parts):
    image = np.zeros(shape, dtype=np.uint8)
    mask = np.full(shape, 255, dtype=np.uint8)
    tiles, masks, bounds = detection.get_clip_images(image, mask, parts)
    covered = np.zeros(shape, dtype=bool)
    for tile, tile_mask, (x, y, w, h) in zip(tiles, masks, bounds):
        assert tile.size == (w, h)
        assert tile_mask.shape == (h, w)
        covered[y:y + h, x:x + w] = True
        tile.close()
    assert covered.all()


def test_detection_failure_preserves_other_surface_result(tmp_path, monkeypatch):
    first = integration(tmp_path)
    second = integration(tmp_path)
    first.key, second.key = "S", "L"
    seen = []

    def detect(data, deadline=None):
        seen.append(data.key)
        if data.key == "S":
            raise ValueError("invalid model response")
        data.set_defect_dict({})

    monkeypatch.setattr(detection, "detection", detect)
    errors = detection.detection_all([first, second])
    assert errors == {"S": "invalid model response"}
    assert seen == ["S", "L"]
    assert first.defect_dict is None
    assert second.defect_dict == {}


def test_radial_recovery_never_invents_a_hole_in_solid_disk():
    import cv2
    from Base.tools import tool

    mask = np.zeros((240, 240), dtype=np.uint8)
    cv2.circle(mask, (120, 120), 100, 255, -1)
    assert tool.get_inner_ellipse_by_mask(mask) is None


def test_stitched_quarter_turn_swaps_pixel_scales(tmp_path, monkeypatch):
    from test_camera_depth_plane_alignment import _load_light_image_mosaic_module, _camera_data

    module = _load_light_image_mosaic_module(monkeypatch)
    data = integration(tmp_path)
    data.key = "X"
    data.datas = [_camera_data("cam", 1000, 0.25, 3000)]
    mosaic = module.ImageMosaic.__new__(module.ImageMosaic)
    mosaic.rotate = 90
    mosaic.direction = "R"
    mosaic.__stitching__(data)
    assert data.scan3dCoordinateScaleX == 0.8
    assert data.scan3dCoordinateScaleY == 0.5
    assert data.export_json()["scan3dCoordinateScaleX"] == 0.8


def test_redetection_websocket_rejects_bad_message_and_accepts_next(monkeypatch):
    import asyncio
    import json
    from api import ApiServer
    from starlette.websockets import WebSocketDisconnect

    accepted = []
    errors = []
    runtime = SimpleNamespace(
        set_re_detection_by_coil_id=lambda a, b: accepted.append((a, b)),
        get_re_detection_msg=lambda: {},
    )
    monkeypatch.setattr(ApiServer, "_runtime_available", lambda: True)
    monkeypatch.setattr(ApiServer.Globs, "imageMosaicThread", runtime)
    messages = iter(["{", "[]", "{}", '{"from_id":true,"to_id":2}',
                     json.dumps({"from_id": 1, "to_id": 2})])

    class Socket:
        async def accept(self):
            pass

        async def receive_text(self):
            try:
                return next(messages)
            except StopIteration:
                raise WebSocketDisconnect()

        async def send_json(self, data):
            errors.append(data)

    asyncio.run(ApiServer.ws_re_detection_task(Socket()))
    assert len(errors) == 4
    assert all("error" in item for item in errors)
    assert accepted == [(1, 2)]


def test_alarm_failure_reaches_coil_status_and_redetection(tmp_path, monkeypatch):
    import importlib
    from contextlib import nullcontext
    from CoilDataBase import CoilSummary

    module = importlib.import_module("SplicingService.ImageMosaicThread")
    data = integration(tmp_path)
    data.set_npy_data(np.ones((8, 10)))
    coordinator = module.ImageMosaicThread.__new__(module.ImageMosaicThread)
    coordinator.saveDataBase = True
    coordinator.re_detection_running = True
    coordinator.re_detection_error = ""
    coordinator.add_msg = lambda message: None
    coordinator._record_scan_attempt = lambda *args: None
    coordinator._update_missing_output_retry = lambda *args: None
    coordinator.imageMosaicList = [SimpleNamespace(
        key="S", set_coil_id=lambda *a, **k: True, get_data=lambda **k: data)]
    saved = []
    monkeypatch.setattr(module.Coil, "addCoil", saved.append)
    monkeypatch.setattr(module, "CoilSession", nullcontext)
    monkeypatch.setattr(CoilSummary, "sync_coil_summary", lambda *args: None)
    monkeypatch.setattr(module, "isLoc", False)
    monkeypatch.setattr(module.cv_detection, "detection_all", lambda items: {})
    monkeypatch.setattr(module.AlarmDetection.detection, "detection_all",
                        lambda items: {"S": ["alarm_info_commit: db unavailable"]})

    assert coordinator._process_secondary_coil(
        SimpleNamespace(Id=123), 123, 0, check_detection=False) == (True, 1)
    assert saved[0]["Status_S"] == module.ErrorMap["ImageError"]
    assert "alarm_info_commit: db unavailable" in saved[0]["Msg"]
    assert "db unavailable" in coordinator.re_detection_error


def test_qml_flat_roll_displays_calibrated_diameter_and_level():
    import json

    QtCore = pytest.importorskip("PySide6.QtCore")
    QtGui = pytest.importorskip("PySide6.QtGui")
    QtQml = pytest.importorskip("PySide6.QtQml")
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
    engine = QtQml.QQmlEngine()
    component = QtQml.QQmlComponent(engine, QtCore.QUrl.fromLocalFile(str(
        ROOT / "app/UI/MotionStudio/qml/Pages/AlarmPage/AlarmCore/CoreFlatRoll.qml")))
    item = component.create()
    assert item is not None, [error.toString() for error in component.errors()]
    item.setProperty("data", {"L": {}, "S": {"inner_circle_width": 20, "accuracy_x": 2,
        "level": 3, "data": json.dumps({"inner_diameter_mm": 20, "inner_ellipse_angle": 90})}})
    app.processEvents()
    assert item.property("innerDiameterMm") == 20
    assert item.property("alarmLevel") == 3
    item.setProperty("data", {"S": {"inner_circle_width": 2000, "accuracy_x": 0.34,
                                    "data": "{"}})
    app.processEvents()
    assert item.property("innerDiameterMm") == 680
    assert item.property("alarmLevel") == 1
