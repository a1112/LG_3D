import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "Base",
        PROJECT_ROOT / "app" / "algorithm_runtime",
        PROJECT_ROOT / "app" / "Server",
        PROJECT_ROOT / "package" / "CoilDataBase",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


import AlarmDetection.DataProcessing.TaperShape as taper_processing


def test_taper_shape_detection_skips_recoverable_angle_errors(monkeypatch):
    warnings = []
    calls = []

    def fake_detection(data_integration, rotation_angle):
        calls.append(rotation_angle)
        if rotation_angle == 0:
            raise TypeError("bad center data")
        if rotation_angle == 90:
            raise AttributeError("missing flat roll center")
        if rotation_angle == 180:
            raise OverflowError("bad coordinate")
        return f"line-{rotation_angle}"

    data_integration = SimpleNamespace(coilId=1001, surface="S")
    monkeypatch.setattr(taper_processing, "TAPER_ROTATION_STEP", 90)
    monkeypatch.setattr(
        taper_processing,
        "detection_taper_shape_by_rotation_angle",
        fake_detection,
    )
    monkeypatch.setattr(taper_processing.logger, "warning", warnings.append)

    result = taper_processing._detection_taper_shape_(data_integration)

    assert calls == [0, 90, 180, 270]
    assert result == {270: "line-270"}
    assert len(warnings) == 3
    assert "0" in warnings[0]
    assert "bad center data" in warnings[0]
    assert "90" in warnings[1]
    assert "missing flat roll center" in warnings[1]
    assert "180" in warnings[2]
    assert "bad coordinate" in warnings[2]


def test_taper_shape_detection_recovery_logs_without_coil_id(monkeypatch):
    warnings = []

    def fake_detection(data_integration, rotation_angle):
        raise ValueError("invalid taper line")

    data_integration = SimpleNamespace(key="L")
    monkeypatch.setattr(taper_processing, "TAPER_ROTATION_STEP", 180)
    monkeypatch.setattr(
        taper_processing,
        "detection_taper_shape_by_rotation_angle",
        fake_detection,
    )
    monkeypatch.setattr(taper_processing.logger, "warning", warnings.append)

    result = taper_processing._detection_taper_shape_(data_integration)

    assert result == {}
    assert len(warnings) == 2
    assert "L" in warnings[0]
    assert "0" in warnings[0]
    assert "invalid taper line" in warnings[0]
    assert "180" in warnings[1]
