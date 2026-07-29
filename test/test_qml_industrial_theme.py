import re
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MOTION_STUDIO_ROOT = PROJECT_ROOT / "app" / "UI" / "MotionStudio"
QML_ROOT = MOTION_STUDIO_ROOT / "qml"


THEMED_SURFACE_FILES = [
    QML_ROOT / "App.qml",
    QML_ROOT / "AppBase.qml",
    QML_ROOT / "MainLayout.qml",
    QML_ROOT / "Core" / "CoreStyle.qml",
    QML_ROOT / "Comp" / "Card" / "CardBase.qml",
    QML_ROOT / "Pages" / "Header" / "TopHeader.qml",
    QML_ROOT / "Pages" / "Header" / "TopTabBar.qml",
    QML_ROOT / "Pages" / "Header" / "CheckRec.qml",
    QML_ROOT / "Pages" / "LeftPage" / "LeftPageView.qml",
    QML_ROOT / "Pages" / "LeftPage" / "DataList" / "DataListView.qml",
    QML_ROOT / "Pages" / "LeftPage" / "DataList" / "DataListViewItenBase.qml",
    QML_ROOT / "Pages" / "LeftPage" / "DataList" / "ListTitleView.qml",
    QML_ROOT / "DataShow" / "_base_" / "DataShowBackground.qml",
    QML_ROOT / "DataShow" / "DataHeader" / "DataShowItemSelectView.qml",
    QML_ROOT / "DataShow" / "DataHeader" / "CheckRecItem.qml",
    QML_ROOT / "DataShow" / "Header" / "View3DChangeItem.qml",
    QML_ROOT / "DataShow" / "DataHeader" / "DataShowItem" / "ShowCharts" / "ChartHead.qml",
    QML_ROOT / "Style" / "StyleMenu.qml",
]


def read_qml(relative_path):
    return (QML_ROOT / relative_path).read_text(encoding="utf-8")


def test_dark_theme_defines_industrial_solid_color_tokens():
    text = read_qml(Path("Core") / "CoreStyle.qml")

    assert 'name: "黑色主题"' in text
    assert 'name: "白色主题"' in text
    assert 'name: "蓝色主题"' in text
    for removed_theme in ("ocean", "forest", "purple", "sunset", "海洋主题", "森林主题", "紫色主题", "日落主题"):
        assert removed_theme not in text
    for token in (
        "appBackgroundColor",
        "panelBackgroundColor",
        "panelElevatedColor",
        "panelAlternateColor",
        "headerBackgroundColor",
        "headerBorderColor",
        "buttonHoverColor",
        "selectionColor",
    ):
        assert f"property color {token}" in text
        assert f"{token} =" in text


def test_main_window_and_layout_use_solid_theme_backgrounds():
    app_base = read_qml(Path("AppBase.qml"))
    app = read_qml(Path("App.qml"))
    main_layout = read_qml(Path("MainLayout.qml"))

    assert 'color: "transparent"' not in app_base
    assert 'color: "transparent"' not in app
    assert "color: coreStyle.appBackgroundColor" in app
    assert "color: coreStyle.appBackgroundColor" in main_layout
    assert "Material.background: coreStyle.panelBackgroundColor" in app


def test_main_layout_lazy_loads_non_initial_pages():
    main_layout = read_qml(Path("MainLayout.qml"))

    assert "Loader {" in main_layout
    assert 'source: "DataShowRoot.qml"' in main_layout
    assert 'source: "DefectShowRoot.qml"' in main_layout
    assert "active: StackLayout.isCurrentItem || status === Loader.Ready" in main_layout


def test_server_connect_refresh_is_deferred_until_after_startup():
    core_state = read_qml(Path("Core") / "CoreState.qml")

    assert "id: connectServerFlushTimer" in core_state
    assert "interval: 300" in core_state
    assert "onTriggered: coreSignal.flush_app()" in core_state
    assert "connectServerFlushTimer.restart()" in core_state
    assert "if (connectServer){\n            coreSignal.flush_app()" not in core_state


def test_primary_chrome_files_do_not_use_transparent_or_alpha_backgrounds():
    forbidden_patterns = [
        re.compile(r'color\s*:\s*"transparent"'),
        re.compile(r'color\s*:\s*"#00000000"', re.IGNORECASE),
        re.compile(r"rgba\s*\("),
        re.compile(r"opacity\s*:"),
    ]

    violations = []
    for path in THEMED_SURFACE_FILES:
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            if pattern.search(text):
                violations.append(f"{path.relative_to(PROJECT_ROOT)} matches {pattern.pattern}")

    assert violations == []


def test_common_dark_theme_text_uses_theme_colors():
    checked_files = [
        Path("DataShow") / "2dShow" / "ShowInfos.qml",
        Path("DataShow") / "ViewArea" / "ShowInfos.qml",
        Path("DataShow") / "DataShowLabels" / "Base" / "RowInputItem.qml",
        Path("DataShow") / "DataShowLabels" / "Base" / "RowSpinBoxItem.qml",
        Path("DataShow") / "DataShowLabels" / "Base" / "RowLabelShow.qml",
        Path("SettingPage") / "OtherSetting" / "OtherSetting.qml",
        Path("SettingPage") / "InfoSetting" / "InfoSetting.qml",
    ]
    hardcoded_dim_text = ("#747474", "#666666", "#333333")

    for relative_path in checked_files:
        text = read_qml(relative_path)
        for color in hardcoded_dim_text:
            assert color not in text
        assert "coreStyle.labelColor" in text or "coreStyle.textColor" in text


def test_style_menu_applies_complete_theme_presets():
    text = read_qml(Path("Style") / "StyleMenu.qml")

    assert 'coreStyle.applyTheme("dark")' in text
    assert 'coreStyle.applyTheme("light")' in text
    assert 'coreStyle.applyTheme("blue")' in text
    for removed_theme in ("ocean", "forest", "purple", "sunset"):
        assert f'coreStyle.applyTheme("{removed_theme}")' not in text
    assert "coreStyle.isDark=true" not in text
    assert "coreStyle.isDark=false" not in text


def test_top_header_icon_does_not_open_theme_menu():
    top_header_text = read_qml(Path("Pages") / "Header" / "TopHeader.qml")

    assert "popManage.popupStyleMenu()" not in top_header_text


def test_display_style_system_is_available_from_settings():
    style_text = read_qml(Path("Core") / "CoreStyle.qml")
    settings_text = read_qml(Path("SettingPage") / "SettingPageView.qml")
    style_settings_text = read_qml(Path("SettingPage") / "StyleSetting" / "StyleSetting.qml")

    assert "property string displayStyleName" in style_text
    assert "readonly property var displayStyles" in style_text
    assert "function applyDisplayStyle(styleKey)" in style_text
    assert "property alias displayStyleName" in style_text
    assert 'import "StyleSetting"' in settings_text
    assert 'qsTr("风格")' in settings_text
    assert "StyleSetting {}" in settings_text
    assert 'qsTr("主题调试")' in style_settings_text
    assert 'qsTr("显示风格")' in style_settings_text
    assert "coreStyle.applyTheme(themeKey)" in style_settings_text
    assert "coreStyle.applyDisplayStyle(styleKey)" in style_settings_text
    for theme_key in ("dark", "light", "blue"):
        assert f'"{theme_key}"' in style_settings_text
    for removed_theme in ("ocean", "forest", "purple", "sunset"):
        assert f'"{removed_theme}"' not in style_settings_text


def test_frameless_window_uses_standard_caption_controls():
    app_text = read_qml(Path("App.qml"))
    title_text = read_qml(Path("Pages") / "Header" / "TitleLabel.qml")
    fill_text = read_qml(Path("Pages") / "Header" / "FillLayout.qml")
    top_header_text = read_qml(Path("Pages") / "Header" / "TopHeader.qml")
    caption_button_text = read_qml(Path("Pages") / "Header" / "WindowCaptionButton.qml")

    assert "onVisibilityChanged" in app_text
    assert "control.visibility = visibility" in app_text
    assert "Window.Maximized" in title_text
    assert "Window.Maximized" in fill_text
    assert "Qt.callLater" in title_text
    assert "Qt.callLater" in fill_text
    assert top_header_text.count("WindowCaptionButton") >= 2
    for button_type in ("minimize", "maximize", "restore", "close"):
        assert f'"{button_type}"' in caption_button_text


def test_caption_button_icons_are_centered_inside_button_frame():
    caption_button_text = read_qml(Path("Pages") / "Header" / "WindowCaptionButton.qml")
    top_header_text = read_qml(Path("Pages") / "Header" / "TopHeader.qml")
    help_button_text = read_qml(Path("Pages") / "Header" / "HelpButton.qml")
    tools_button_text = read_qml(Path("Pages") / "Header" / "TopToolsButton.qml")

    assert "contentItem: Item" in caption_button_text
    assert "Canvas {" in caption_button_text
    assert "anchors.centerIn: parent" in caption_button_text
    assert "width: parent.width" in caption_button_text
    assert "height: parent.height" in caption_button_text
    assert "height: coreStyle.topHeight" in top_header_text
    assert "height: 35" not in top_header_text
    assert "height: coreStyle.topHeight" in help_button_text
    assert "width: coreStyle.windowButtonWidth" in help_button_text
    assert "height: coreStyle.topHeight" in tools_button_text
    assert "width: coreStyle.windowButtonWidth" in tools_button_text


def test_data_view_tools_use_icon_popups():
    tool_buttons_text = read_qml(Path("DataShow") / "Foot" / "ToolBtns.qml")

    assert "ToolPopupButton" in tool_buttons_text
    assert 'iconName: "MourceArray"' in tool_buttons_text
    assert 'iconName: "survey"' in tool_buttons_text
    assert 'popupTitle: qsTr("自由查看")' in tool_buttons_text
    assert 'popupTitle: qsTr("测量工具")' in tool_buttons_text
    assert "dataShowCore.controls.currentMouseModel = dataShowCore.controls.mouseMoveModel" in tool_buttons_text
    assert "dataShowCore.controls.currentMouseModel = dataShowCore.controls.mouseSurveyModel" in tool_buttons_text


def test_simulated_3d_view_uses_local_runtime_obj_loader():
    node_text = read_qml(Path("DataShow") / "View3D" / "Node3D.qml")
    surface_text = read_qml(Path("Core") / "Surface" / "SurfaceData.qml")
    toolbox_text = read_qml(Path("DataShow") / "ViewChang" / "ToolBoxViewRow.qml")

    assert "import QtQuick3D.AssetUtils" in node_text
    assert "RuntimeLoader" in node_text
    assert "testDataMeshUrl" in node_text
    assert "file:////\"+api.apiConfig.hostname" not in node_text
    assert "testDataMeshPath" in surface_text
    assert "testDataMeshExists" in surface_text
    assert "testDataMeshExists" in toolbox_text


def test_initial_coil_selection_refreshes_after_async_list_load():
    init_text = read_qml(Path("Core") / "Init.qml")

    assert "initCoilBatchTimer" in init_text
    assert "function appendPendingCoils()" in init_text
    assert "initCoilByData(parsed)" in init_text
    assert "pendingCoilData = coilData" in init_text
    assert "core.setCoilIndex(0)" in init_text
    assert "isListLoading = false" in init_text
    assert init_text.index("function appendPendingCoils()") < init_text.index("core.setCoilIndex(0)")


def test_api_list_delegate_width_does_not_depend_on_null_parent():
    api_list_text = read_qml(Path("PopupView") / "ApiListPop" / "ApiListPopView.qml")

    assert "id: apiListView" in api_list_text
    assert "width: apiListView.width" in api_list_text
    assert "width: parent.width" not in api_list_text


def test_rust_services_use_fixed_ports_and_test_api_defaults_to_python():
    api_config_text = read_qml(Path("Api") / "ApiConfig.qml")
    core_setting_text = read_qml(Path("Core") / "CoreSetting.qml")
    api_database_text = read_qml(Path("Api") / "Api_DataBase.qml")
    connect_dialog_text = read_qml(Path("PopupView") / "Connect" / "ConnectDialog.qml")
    general_setting_text = read_qml(Path("SettingPage") / "GeneralSetting" / "GeneralSetting.qml")

    assert "property bool useRustImageServer: true" in core_setting_text
    assert "property bool useRustTestServer: false" in core_setting_text
    assert "imageServerBackendDefaultVersion < currentImageServerBackendDefaultVersion" in core_setting_text
    assert "readonly property int rustApiPort: 5011" in api_config_text
    assert "activeApiPort: coreSetting.useRustTestServer ? rustApiPort : pythonApiPort" in api_config_text
    assert "activeImageServerPort: coreSetting.useRustImageServer ? rustImageServerPort : pythonImageServerPort" in api_config_text
    assert "active: coreSetting.useRustTestServer" in api_database_text
    assert "if (!coreSetting.useRustTestServer)" in api_database_text
    assert "server_port" not in connect_dialog_text
    assert "rustImageServerPort" not in general_setting_text


def test_header_time_text_is_readable_on_dark_theme():
    time_text = read_qml(Path("Base") / "TimeText.qml")

    assert 'color: "#333"' not in time_text
    assert 'coreStyle.isDark ? "#DDEBFF"' in time_text


def test_height_point_websocket_reconnects_after_close():
    api_text = read_qml(Path("Api") / "Api_DataBase.qml")

    assert "Timer {" in api_text
    assert "id: heightPointReconnectTimer" in api_text
    assert "function _scheduleHeightPointReconnect()" in api_text
    assert "active: coreSetting.useRustTestServer && _heightPointConnectEnabled" in api_text
    assert "heightPointSocket.active =" not in api_text
    assert "_heightPointReconnectDelayMs * 2" in api_text
    assert "_heightPointReconnectMaxDelayMs" in api_text
    assert "_scheduleHeightPointReconnect()" in api_text


def test_area_tiles_use_column_for_x_and_row_for_y():
    view_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageView.qml")
    item_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageItem.qml")

    assert "x: parseInt(index % count_) * width" in view_text
    assert "y: parseInt(index / count_) * height" in view_text
    assert "row_: parseInt(index/count_)" in view_text
    assert "col_: parseInt(index%count_)" in view_text
    assert "targetSourceMissing" in item_text
    assert "if (oldTargetLevel !== targetLevel || urlChanged || targetSourceMissing)" in item_text


def test_area_low_resolution_levels_load_the_complete_grid():
    view_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageView.qml")
    item_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageItem.qml")

    assert "readonly property bool loadCompleteGrid: enableParallelLoad || currentLevel <= 1" in view_text
    assert "enableParallelLoad: root.loadCompleteGrid" in view_text
    assert "if (enableParallelLoad) {\n            return true\n        }\n        return isInViewport" in item_text
    assert "onCurrentLevelChanged: {\n        if (shouldLoad)" in item_text


def test_2d_view_key_uses_area_image_endpoint():
    api_text = read_qml(Path("Api") / "Api.qml")
    surface_text = read_qml(Path("Core") / "Surface" / "SurfaceData.qml")
    area_core_text = read_qml(Path("DataShow") / "Core" / "DataShowAreaCore.qml")

    assert '_viewKey_ = _viewKey_ === "2D" ? "AREA" : _viewKey_' in api_text
    assert "function normalizeViewKey(viewKey)" in surface_text
    assert 'return viewKey === "2D" ? "AREA" : viewKey' in surface_text
    assert "function refreshAreaSource()" in surface_text
    assert "refreshAreaSource()\n        rootViewIndex = 2" in surface_text
    assert "onKeyChanged: {\n        rebuildViewHasData()\n        refreshAreaSource()\n    }" in surface_text
    assert "surfaceData.refreshAreaSource()" in area_core_text


def test_2d_area_context_menu_can_rebuild_tile_cache():
    api_text = read_qml(Path("Api") / "Api.qml")
    area_core_text = read_qml(Path("DataShow") / "Core" / "DataShowAreaCore.qml")
    menu_text = read_qml(Path("DataShow") / "Menu" / "MainShow" / "MainShowMenu.qml")

    assert "function recacheAreaTiles(surfaceKey, coilId, viewKey, success, failure)" in api_text
    assert 'let url = apiConfig.serverUrl\n                + "/image/area/cache/rebuild/"' in api_text
    assert '"/image/area/cache/rebuild/"' in api_text
    assert "function clearRustImageCache(success, failure)" in api_text
    assert '"/cache/clear"' in api_text
    assert "property int areaCacheVersion" in area_core_text
    assert "property bool recacheInProgress" in area_core_text
    assert "property string lastRecacheMessage" in area_core_text
    assert "api.clearRustImageCache" in area_core_text
    assert "areaCacheVersion += 1" in area_core_text
    assert "function recacheAreaTiles()" in area_core_text
    assert "canRecacheAreaTiles" in menu_text
    assert "dataShowCore_.recacheAreaTiles()" in menu_text
    assert "\\u91cd\\u65b0\\u7f13\\u5b582D\\u56fe\\u50cf" in menu_text


def test_2d_defects_share_defect_class_visibility_list():
    defect_class_text = read_qml(Path("Property") / "DefectClassProperty.qml")
    data_show_core_text = read_qml(Path("DataShow") / "Core" / "_base_" / "DataShowCore_.qml")
    filter_core_text = read_qml(Path("DefectPage") / "Core" / "FilterCore.qml")

    assert "function shared_defect_name(defectName)" in defect_class_text
    assert "return name.slice(3)" in defect_class_text
    assert "function normalize_defect_dict_data(data)" in defect_class_text
    assert 'if (sharedName in normalized)' in defect_class_text
    assert "let sharedName = global.defectClassProperty.shared_defect_name(defectName)" in data_show_core_text
    assert "let sharedName = global.defectClassProperty.shared_defect_name(name)" in filter_core_text


def test_qml_resource_file_builds(tmp_path):
    rcc = PROJECT_ROOT / ".venv" / "Scripts" / "pyside6-rcc.exe"
    if not rcc.exists():
        rcc = PROJECT_ROOT / ".venv" / "Scripts" / "pyside6-rcc"
    if not rcc.exists():
        rcc = shutil.which("pyside6-rcc")
    assert rcc, "pyside6-rcc is required to build qml.qrc"
    output_file = tmp_path / "qml-test.rcc"

    completed = subprocess.run(
        [str(rcc), str(MOTION_STUDIO_ROOT / "qml.qrc"), "--binary", "-o", str(output_file)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert output_file.exists()
    assert output_file.stat().st_size > 0
