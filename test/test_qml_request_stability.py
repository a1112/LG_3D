from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QML_ROOT = REPO_ROOT / "app" / "UI" / "MotionStudio" / "qml"


def _read(relative_path: str) -> str:
    return (QML_ROOT / relative_path).read_text(encoding="utf-8")


def _function_body(source: str, function_name: str, next_marker: str) -> str:
    start = source.index(f"function {function_name}")
    end = source.index(next_marker, start)
    return source[start:end]


def test_same_coil_flush_returns_before_reload_fanout() -> None:
    source = _read("Core/Core.qml")
    flush_body = _function_body(source, "flushListItem", "function flushList()")

    # API coil-list rows expose Id. A SecondaryCoilId-only comparison made
    # every periodic /flush look like a new coil and reloaded both surfaces.
    assert "c_data.Id !== undefined" in flush_body
    guard = "nextCoilId === Number(currentCoilModel.coilId)"
    assert guard in flush_body
    assert flush_body.index(guard) < flush_body.index("currentCoilModel.init(c_data)")
    assert flush_body.index("return", flush_body.index(guard)) < flush_body.index(
        "coreModel.surfaceS.setCoilId"
    )
    assert "coreControl.init_data_has()" in flush_body


def test_height_data_is_singleflight_and_backs_off_after_overload() -> None:
    source = _read("Core/Surface/SurfaceData.qml")
    request_body = _function_body(source, "updataHeightData", "id: heightDataDebounceTimer")

    assert "if (heightDataRequest)" in request_body
    assert "heightDataPending = true" in request_body
    assert request_body.index("if (heightDataRequest)") < request_body.index(
        "heightDataRequest = api.getHeightData"
    )
    assert "heightDataRequest.abort()" not in request_body
    assert "nowMs < heightDataRetryAfter" in request_body
    assert "heightDataDebounceTimer.interval = Math.max(" in request_body
    assert "heightDataRetryAfter" in request_body
    assert "status === 0 || status === 429 || status === 503" in request_body
    assert "new Date().getTime() + 3000" in request_body
    assert "interval: 100" in source

    switch_body = _function_body(source, "setCoilId", "Component.onDestruction")
    assert "heightDataRequest.abort()" in switch_body
    assert "heightDataRequestId += 1" in switch_body


def test_qml_http_requests_timeout_and_pollers_do_not_overlap() -> None:
    ajax = _read("Api/Ajax.qml")
    assert "property int requestTimeoutMs: 12000" in ajax
    assert "xhr.abort()" in ajax
    assert 'failure("request timeout", 0)' in ajax
    assert "return xhr" in ajax

    expected_guards = {
        "Api/Api_Base.qml": "delayRequestRunning",
        "Pages/AlarmPage/AlarmItem/AlarmHardware.qml": "requestRunning",
        "Pages/AlarmPage/AlarmItem/AlarmItemCameras.qml": "requestRunning",
    }
    for relative_path, guard_name in expected_guards.items():
        source = _read(relative_path)
        assert guard_name in source
        assert (
            f"if ({guard_name})" in source
            or f"if (root.{guard_name})" in source
        )


def test_quick_exports_use_get_download_overload() -> None:
    source = _read("PopupView/Export/ExportView.qml")

    for endpoint in ("Today", "1h", "24h"):
        call = (
            f"fileDownloader.downloadFile(api.getExport{endpoint}Url(),"
            "root.exportUrl)"
        )
        assert call in source
        assert call[:-1] + ',\"\")' not in source


def test_height_point_websocket_keeps_binding_and_limits_disconnect_fallback() -> None:
    source = _read("Api/Api_DataBase.qml")

    assert "active: coreSetting.useRustTestServer && _heightPointConnectEnabled" in source
    assert "heightPointSocket.active =" not in source
    assert "function onUseRustTestServerChanged()" in source
    assert "_heightPointReconnectMaxDelayMs: 30000" in source
    assert "_heightPointPendingLimit: 16" in source
    assert "latestRequestId" in source
    assert '? "ws error" : "superseded"' in source


def test_alarm_network_polling_is_centralized_and_unique_per_port() -> None:
    group = _read("Pages/AlarmPage/AlarmItem/AlarmItemNet.qml")
    delegate = _read("Pages/AlarmPage/AlarmItem/AlarmItemNetItem.qml")

    assert "uniquePorts.indexOf(portNumber) < 0" in group
    assert "if (requestRunning)" in group
    assert "running: root.visible && root.pollingEnabled" in group
    assert "Timer" not in delegate
    assert "__getDelay__" not in delegate


def test_tile_metadata_request_is_cancelled_when_source_changes() -> None:
    source = _read("Controls/TiledImageView/TiledImageView.qml")

    assert "property var _imageInfoRequest" in source
    assert "_imageInfoRequest.abort()" in source
    assert "Component.onDestruction" in source
