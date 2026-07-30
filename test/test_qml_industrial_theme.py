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
        "statusSuccessColor",
        "statusWarningColor",
        "statusErrorColor",
        "statusInactiveColor",
        "secondaryTextColor",
        "infoOverlayColor",
        "infoOverlayBorderColor",
        "viewportBackgroundColor",
    ):
        assert f"property color {token}" in text
        if token in {
            "appBackgroundColor",
            "panelBackgroundColor",
            "panelElevatedColor",
            "panelAlternateColor",
            "headerBackgroundColor",
            "headerBorderColor",
            "buttonHoverColor",
            "selectionColor",
        }:
            assert f"{token} =" in text


def test_main_window_and_layout_use_solid_theme_backgrounds():
    app_base = read_qml(Path("AppBase.qml"))
    app = read_qml(Path("App.qml"))
    main_layout = read_qml(Path("MainLayout.qml"))

    assert 'color: "transparent"' not in app_base
    assert 'color: "transparent"' not in app
    assert "color: coreStyle.appBackgroundColor" in app
    assert "color: root.style.appBackgroundColor" in main_layout
    assert "Material.background: coreStyle.panelBackgroundColor" in app


def test_main_layout_lazy_loads_non_initial_pages():
    main_layout = read_qml(Path("MainLayout.qml"))

    assert "Loader {" in main_layout
    assert "sourceComponent: DataShowRoot {" in main_layout
    assert "sourceComponent: DefectShowRoot {" in main_layout
    assert "modelStore: root.model" in main_layout
    assert "globalContext: root.globalContext" in main_layout
    assert "toolService: root.toolService" in main_layout
    assert "active: StackLayout.isCurrentItem || status === Loader.Ready" in main_layout


def test_server_connect_refresh_is_deferred_until_after_startup():
    core_state = read_qml(Path("Core") / "CoreState.qml")

    assert "id: connectServerFlushTimer" in core_state
    assert "interval: 300" in core_state
    assert "required property var signalController" in core_state
    assert "onTriggered: root.signalController.flush_app()" in core_state
    assert "connectServerFlushTimer.restart()" in core_state
    assert "if (connectServer){\n            coreSignal.flush_app()" not in core_state


def test_live_polling_runs_only_while_connected_and_uses_explicit_dependencies():
    timer_text = read_qml(Path("Core") / "CoreTimer.qml")

    for dependency in ("apiClient", "model", "settings", "initController", "connectionState"):
        assert f"required property var {dependency}" in timer_text
    assert "running: root.connectionState.connected" in timer_text
    assert "dataFlushBusy || !connectionState.connected || initController.isListLoading" in timer_text
    assert "property string lastDataFlushError" in timer_text


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
        Path("SettingPage") / "OtherSetting" / "OtherSetting.qml",
        Path("SettingPage") / "InfoSetting" / "InfoSetting.qml",
    ]
    hardcoded_dim_text = ("#747474", "#666666", "#333333")

    for relative_path in checked_files:
        text = read_qml(relative_path)
        for color in hardcoded_dim_text:
            assert color not in text
        assert (
            "coreStyle.labelColor" in text
            or "coreStyle.textColor" in text
                or "style.textColor" in text
                or "root.style.labelColor" in text
                or "root.style.textColor" in text
                or "root.style.secondaryTextColor" in text
        )


def test_data_overlays_and_defect_filters_use_semantic_theme_tokens():
    style_text = read_qml(Path("Core") / "CoreStyle.qml")
    defect_filter_text = read_qml(
        Path("DefectPage") / "DefectInfo" / "DefectFlowRowItem.qml"
    )
    data_core_text = read_qml(Path("DataShow") / "Core" / "DataShowCore.qml")
    overlay_files = (
        Path("DataShow") / "2dShow" / "ShowInfos.qml",
        Path("DataShow") / "ViewArea" / "ShowInfos.qml",
    )

    assert "property color infoOverlayColor" in style_text
    assert "property color secondaryTextColor" in style_text
    assert "isDarkTheme" not in defect_filter_text
    assert "required property var style" in defect_filter_text
    assert "style.secondaryTextColor" in defect_filter_text
    assert 'imageTypeColor: "#999999"' not in data_core_text
    assert 'imageTypeColor = "#52c41a"' not in data_core_text
    assert "root.style.statusInactiveColor" in data_core_text
    assert "root.style.statusSuccessColor" in data_core_text
    for relative_path in overlay_files:
        text = read_qml(relative_path)
        assert "#772e2e2e" not in text
        assert "required property var style" in text
        assert "style.infoOverlayColor" in text
        assert "style.infoOverlayBorderColor" in text


def test_style_menu_applies_complete_theme_presets():
    text = read_qml(Path("Style") / "StyleMenu.qml")

    assert 'root.style.applyTheme("dark")' in text
    assert 'root.style.applyTheme("light")' in text
    assert 'root.style.applyTheme("blue")' in text
    for removed_theme in ("ocean", "forest", "purple", "sunset"):
        assert f'applyTheme("{removed_theme}")' not in text
    assert ".isDark=true" not in text
    assert ".isDark=false" not in text


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
    assert "StyleSetting {" in settings_text
    assert 'qsTr("主题调试")' in style_settings_text
    assert 'qsTr("显示风格")' in style_settings_text
    assert "root.style.applyTheme(themeTile.themeKey)" in style_settings_text
    assert (
        "root.style.applyDisplayStyle(styleTile.styleKey)"
        in style_settings_text
    )
    for theme_key in ("dark", "light", "blue"):
        assert f'"{theme_key}"' in style_settings_text
    for removed_theme in ("ocean", "forest", "purple", "sunset"):
        assert f'"{removed_theme}"' not in style_settings_text


def test_settings_hide_unimplemented_alarm_and_3d_pages():
    settings_text = read_qml(Path("SettingPage") / "SettingPageView.qml")
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")

    assert 'qsTr("报警")' not in settings_text
    assert 'qsTr("3D 渲染")' not in settings_text
    assert "AlarmSetting {}" not in settings_text
    assert "D3Setting {}" not in settings_text
    for removed_path in (
        Path("SettingPage") / "AlarmSetting" / "AlarmSetting.qml",
        Path("SettingPage") / "D3Setting" / "D3Setting.qml",
        Path("SettingPage") / "BaseSetting" / "BaseSetting.qml",
    ):
        assert not (QML_ROOT / removed_path).exists()
        assert f"qml/{removed_path.as_posix()}" not in qrc_text


def test_frameless_window_uses_standard_caption_controls():
    app_text = read_qml(Path("App.qml"))
    title_text = read_qml(
        Path("Pages") / "Header" / "WindowTitleLabel.qml"
    )
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
    assert "height: root.style.topHeight" in top_header_text
    assert "height: 35" not in top_header_text
    assert "height: root.style.topHeight" in help_button_text
    assert "width: root.style.windowButtonWidth" in help_button_text
    assert "height: root.style.topHeight" in tools_button_text
    assert "width: root.style.windowButtonWidth" in tools_button_text


def test_data_view_tools_use_icon_popups():
    tool_buttons_text = read_qml(Path("DataShow") / "Foot" / "ToolBtns.qml")

    assert "ToolPopupButton" in tool_buttons_text
    assert 'iconName: "MourceArray"' in tool_buttons_text
    assert 'iconName: "survey"' in tool_buttons_text
    assert 'popupTitle: qsTr("自由查看")' in tool_buttons_text
    assert 'popupTitle: qsTr("测量工具")' in tool_buttons_text
    assert (
        "root.controller.controls.currentMouseModel ="
        in tool_buttons_text
    )
    assert "root.controller.controls.mouseMoveModel" in tool_buttons_text
    assert "root.controller.controls.mouseSurveyModel" in tool_buttons_text
    assert "required property var controller" in tool_buttons_text
    assert "required property var style" in tool_buttons_text


def test_simulated_3d_view_uses_local_runtime_obj_loader():
    node_text = read_qml(Path("DataShow") / "View3D" / "Node3D.qml")
    surface_text = read_qml(Path("Core") / "Surface" / "SurfaceData.qml")
    toolbox_text = read_qml(Path("DataShow") / "ViewChang" / "ToolBoxViewRow.qml")

    assert "import QtQuick3D.AssetUtils" in node_text
    assert "RuntimeLoader" in node_text
    assert "required property var surfaceData" in node_text
    assert "root.surfaceData.meshUrl" in node_text
    assert "testDataMeshUrl" in surface_text
    assert "file:////\"+api.apiConfig.hostname" not in node_text
    assert "testDataMeshPath" in surface_text
    assert "testDataMeshExists" in surface_text
    assert "root.surfaceData.meshExits" in toolbox_text
    assert "testDataMeshExists" not in toolbox_text


def test_initial_coil_selection_refreshes_after_async_list_load():
    init_text = read_qml(Path("Core") / "Init.qml")
    controller_text = read_qml(Path("Core") / "CoilListController.qml")
    bootstrap_text = read_qml(Path("Core") / "BootstrapController.qml")

    assert "BootstrapController {" in init_text
    assert "CoilListController {" in init_text
    assert "readonly property alias isListLoading: coilListController.loading" in init_text
    assert "function refreshMetadata(force)" in init_text
    assert "function refreshCoils()" in init_text
    assert "function refreshAll(forceMetadata)" in init_text
    assert "property bool refreshQueued: false" in controller_text
    assert "function _appendBatch()" in controller_text
    assert "interval: 1" in controller_text
    assert "interval: 0" not in controller_text
    assert "coreController.setCoilIndex(0)" in controller_text
    assert "Qt.callLater(refresh)" in controller_text
    assert "property bool loaded: false" in bootstrap_text
    assert "if (loading || (loaded && !force))" in bootstrap_text
    for dependency in ("apiClient", "model", "coreController"):
        assert f"required property var {dependency}" in controller_text
    for dependency in ("apiClient", "model", "appContext"):
        assert f"required property var {dependency}" in bootstrap_text


def test_http_client_tracks_requests_and_accepts_all_success_statuses():
    ajax_text = read_qml(Path("Api") / "Ajax.qml")

    assert "property int activeRequestCount: 0" in ajax_text
    assert "readonly property bool busy: activeRequestCount > 0" in ajax_text
    assert "function finish(status)" in ajax_text
    assert "xhr.status >= 200 && xhr.status < 300" in ajax_text
    assert "root.activeRequestCount = Math.max(0, root.activeRequestCount - 1)" in ajax_text
    assert "request timeout" in ajax_text
    assert 'sendRequest("PUT", url, JSON.stringify(arg), success, failure)' in ajax_text
    assert 'sendRequest("DELETE", url, null, success, failure)' in ajax_text
    assert 'method === "PUT"' in ajax_text


def test_connection_health_uses_elapsed_time_and_semantic_status():
    api_text = read_qml(Path("Api") / "Api_Base.qml")
    style_text = read_qml(Path("Core") / "CoreStyle.qml")
    footer_text = read_qml(Path("Pages") / "LeftPage" / "FootView.qml")

    assert "failure(delay-startTime)" not in api_text
    assert "failure(delay)" in api_text
    assert "readonly property bool connected: delay >= 0" in api_text
    assert "property int consecutiveDelayFailures: 0" in api_text
    for token in ("statusSuccessColor", "statusWarningColor", "statusErrorColor"):
        assert f"property color {token}" in style_text
    assert "root.apiClient.connectionText" in footer_text
    assert 'text: root.apiClient.delay + " ms"' in footer_text
    assert "baseUrl:" not in footer_text
    for dependency in ("apiClient", "style", "model", "popupManager"):
        assert f"required property var {dependency}" in footer_text


def test_api_list_delegate_width_does_not_depend_on_null_parent():
    api_list_text = read_qml(Path("PopupView") / "ApiListPop" / "ApiListPopView.qml")

    assert "id: apiListView" in api_list_text
    assert "width: apiListView.width" in api_list_text
    assert "width: parent.width" not in api_list_text


def test_high_confidence_qml_member_and_dialog_errors_are_fixed():
    foot_item_text = read_qml(Path("DataShow") / "Foot" / "ItemDelegateItem.qml")
    watermark_text = read_qml(Path("DataShow") / "_base_" / "Watermark.qml")
    global_alarm_text = read_qml(
        Path("PopupView") / "GlobalAlarm" / "GlobalAlarmView.qml"
    )
    redetection_text = read_qml(
        Path("PopupView") / "ReDetection" / "ReDetectionView.qml"
    )
    alg_test_text = read_qml(Path("PopupView") / "AlgTest" / "AlgTestDialog.qml")

    assert not (QML_ROOT / "Base" / "ManualDefectItem.qml").exists()
    assert "Material.text" not in foot_item_text
    assert "required property var style" in watermark_text
    assert "QtQuick3D" not in watermark_text
    assert "particleTriggerRequested" not in watermark_text
    assert "required property int index" in watermark_text
    assert "animItem.item" not in watermark_text
    assert "required property var captureAlarmWatcher" in global_alarm_text
    assert "watcher: root.captureAlarmWatcher" in global_alarm_text
    assert 'property string outputUrl: ""' in redetection_text
    assert alg_test_text.count("FolderDialog {") == 2
    assert "FileDialog.OpenDirectory" not in alg_test_text
    assert "selectedFolder" in alg_test_text


def test_large_monitor_delegates_are_split_and_dependencies_are_explicit():
    app_text = read_qml(Path("App.qml"))
    app_base_text = read_qml(Path("AppBase.qml"))
    pops_text = read_qml(Path("PopupView") / "Pops.qml")
    monitor_path = (
        Path("PopupView") / "HardwareMonitor" / "HardwareMonitorView.qml"
    )
    monitor_text = read_qml(monitor_path)
    alg_test_text = read_qml(
        Path("PopupView") / "AlgTest" / "AlgTestDialog.qml"
    )
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")
    component_names = (
        "MonitorCamera2DCard",
        "MonitorCamera3DCard",
        "MonitorNetworkCard",
        "MonitorServiceCard",
        "MonitorOverviewCameraCard",
        "MonitorOverviewNetworkRow",
        "MonitorOverviewServiceRow",
    )

    assert len(monitor_text.splitlines()) < 900
    assert "delegate: Rectangle" not in monitor_text
    assert "app.api" not in monitor_text
    for dependency in ("apiClient", "adaptiveMetrics", "style"):
        assert f"required property var {dependency}" in monitor_text
        assert f"required property var {dependency}" in alg_test_text
    for component_name in component_names:
        assert f"delegate: {component_name}" in monitor_text
        component_path = (
            Path("PopupView")
            / "HardwareMonitor"
            / f"{component_name}.qml"
        )
        component_text = read_qml(component_path)
        assert "required property var style" in component_text
        assert f"<file>qml/{component_path.as_posix()}</file>" in qrc_text
    assert "apiClient: app.api" in app_text
    assert "adaptiveMetrics: app.adaptive" in app_text
    assert "appStyle: app.coreStyle" in app_text
    assert "pragma ComponentBehavior: Bound" in app_base_text
    assert "apiClient: appBase.apiClient" in app_base_text
    assert "apiClient: root.apiClient" in pops_text


def test_settings_runtime_dependencies_are_passed_through_popup_boundary():
    app_text = read_qml(Path("App.qml"))
    app_base_text = read_qml(Path("AppBase.qml"))
    pops_text = read_qml(Path("PopupView") / "Pops.qml")
    settings_view = read_qml(Path("SettingPage") / "SettingPageView.qml")
    style_settings = read_qml(
        Path("SettingPage") / "StyleSetting" / "StyleSetting.qml"
    )
    other_settings = read_qml(
        Path("SettingPage") / "OtherSetting" / "OtherSetting.qml"
    )
    software_update = read_qml(
        Path("SettingPage") / "OtherSetting" / "SoftwareUpdate.qml"
    )

    dependencies = (
        "apiClient",
        "style",
        "settings",
        "appInfo",
        "downloadClient",
    )
    for dependency in dependencies:
        assert f"required property var {dependency}" in settings_view
    for dependency in dependencies:
        assert f"required property var {dependency}" in other_settings
        assert f"required property var {dependency}" in software_update
    assert "required property var style" in style_settings
    assert "coreStyle." not in style_settings
    assert "coreSetting." not in other_settings
    assert "coreStyle." not in other_settings
    assert "coreSetting." not in software_update
    assert "coreStyle." not in software_update
    assert "fileDownloader" not in software_update
    assert "JsonUtils.parse(" in software_update
    assert "settingsStore: app.coreSetting" in app_text
    assert "appInfo: app.coreInfo" in app_text
    assert "downloadClient: fileDownloader" in app_text
    assert "settingsStore: appBase.settingsStore" in app_base_text
    assert "settings: root.settingsStore" in pops_text


def test_clip_settings_share_one_surface_editor_and_report_api_results():
    clip_view = read_qml(
        Path("PopupView") / "ClipSetting" / "ClipSettingView.qml"
    )
    surface_editor_path = (
        Path("PopupView")
        / "ClipSetting"
        / "SurfaceClipSettings.qml"
    )
    surface_editor = read_qml(surface_editor_path)
    pops_text = read_qml(Path("PopupView") / "Pops.qml")
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")

    assert clip_view.count("SurfaceClipSettings {") == 2
    assert len(clip_view.splitlines()) < 90
    assert "coreSetting." not in clip_view
    assert "coreStyle." not in clip_view
    for dependency in ("apiClient", "settings", "style"):
        assert f"required property var {dependency}" in clip_view
        assert f"required property var {dependency}" in surface_editor
    assert "required property string surfaceKey" in surface_editor
    assert "onValueModified: root.setFixedValue(value)" in surface_editor
    assert "if (root.busy)" in surface_editor
    assert "root.apiClient.setAreaClipConfig(" in surface_editor
    assert 'root.statusText = qsTr("配置已应用")' in surface_editor
    assert 'qsTr("应用失败: %1")' in surface_editor
    assert "apiClient: root.apiClient" in pops_text
    assert f"<file>qml/{surface_editor_path.as_posix()}</file>" in qrc_text


def test_primary_data_view_passes_chart_dependencies_from_app_boundary():
    app_text = read_qml(Path("App.qml"))
    main_layout = read_qml(Path("MainLayout.qml"))
    data_root = read_qml(Path("DataShowRoot.qml"))
    data_layout = read_qml(Path("DataShow") / "DataShowLayout.qml")
    data_background = read_qml(
        Path("DataShow") / "_base_" / "DataShowBackground.qml"
    )
    data_view = read_qml(Path("DataShow") / "DataShowView.qml")
    header = read_qml(
        Path("DataShow") / "DataHeader" / "DataHeaderView.qml"
    )
    chart = read_qml(
        Path("DataShow")
        / "DataHeader"
        / "DataShowItem"
        / "DataShowItemCharts.qml"
    )
    info_panel = read_qml(
        Path("DataShow")
        / "DataHeader"
        / "DataShowItem"
        / "DataShowItemInfos.qml"
    )

    for dependency in (
        "adaptiveMetrics",
        "style",
        "model",
        "settings",
        "viewControl",
    ):
        assert f"required property var {dependency}" in main_layout
        assert f"required property var {dependency}" in data_root
        if dependency in ("adaptiveMetrics", "style"):
            assert f"required property var {dependency}" in data_background
        else:
            assert f"required property var {dependency}" in data_layout
    assert "sourceComponent: DataShowRoot {" in main_layout
    assert "source: \"DataShowRoot.qml\"" not in main_layout
    assert "adaptiveMetrics: app.adaptive" in app_text
    assert "model: app.coreModel" in app_text
    assert "settings: app.coreSetting" in app_text
    assert "viewControl: app.control" in app_text
    assert "alarmInfo: app.coreAlarmInfo" in app_text
    for boundary in (main_layout, data_root, data_layout, data_view, header):
        assert "required property var alarmInfo" in boundary
    assert "alarmInfo: root.alarmInfo" in main_layout
    assert "alarmInfo: root.alarmInfo" in data_root
    assert data_layout.count("alarmInfo: root.alarmInfo") == 2
    assert "alarmInfo: root.alarmInfo" in data_view
    assert "alarmInfo: root.alarmInfo" in header
    assert "required property var alarmInfo" in info_panel
    assert "coreAlarmInfo." not in info_panel
    for dependency in ("surfaceData", "controller", "style"):
        assert f"required property var {dependency}" in header
        assert f"required property var {dependency}" in chart
    assert "surfaceData: root.surfaceData" in header
    assert "controller: root.controller" in header
    assert "coreStyle." not in chart
    assert "dataShowCore." not in chart
    assert "onPressed: function(mouse)" in chart
    assert "onPositionChanged: function(mouse)" in chart
    assert "onReleased: function(mouse)" in chart
    assert "required property SurfaceData surfaceData" in data_view
    assert "required property DataShowCore dataShowCore" in data_view


def test_left_alarm_summary_and_coil_menu_use_explicit_app_services():
    app_base = read_qml(Path("AppBase.qml"))
    pops = read_qml(Path("PopupView") / "Pops.qml")
    left_page = read_qml(
        Path("Pages") / "LeftPage" / "LeftPageView.qml"
    )
    alarm_card = read_qml(
        Path("Pages")
        / "AlarmPage"
        / "AlarmItemSimple"
        / "AlarmItemSimple.qml"
    )
    alarm_view = read_qml(
        Path("Pages")
        / "AlarmPage"
        / "AlarmItemSimple"
        / "AlarmItemSimpleView.qml"
    )
    coil_menu = read_qml(
        Path("Pages")
        / "LeftPage"
        / "DataList"
        / "DataListMenu"
        / "DataListItemMenu.qml"
    )

    for dependency in ("modelStore", "clipboardService", "toolService"):
        assert f"property var {dependency}" in app_base
        assert f"required property var {dependency}" in pops
    for dependency in (
        "apiClient",
        "modelStore",
        "clipboardService",
        "toolService",
        "popupManager",
    ):
        assert f"required property var {dependency}" in coil_menu
    assert "coreModel." not in coil_menu
    assert "cpp." not in coil_menu
    assert "tool." not in coil_menu
    assert "popManage." not in coil_menu
    assert "required property var alarmInfo" in left_page
    assert "required property var alarmInfo" in alarm_card
    assert "required property var alarmInfo" in alarm_view
    assert "coreAlarmInfo." not in alarm_view
    assert "api." not in alarm_card


def test_top_header_and_coil_tools_use_explicit_runtime_dependencies():
    main_layout = read_qml(Path("MainLayout.qml"))
    top_header = read_qml(Path("Pages") / "Header" / "TopHeader.qml")
    coil_tools = read_qml(
        Path("Pages") / "Header" / "TopCoilTools.qml"
    )
    top_tools = read_qml(Path("Pages") / "Header" / "TopTools.qml")
    top_tabs = read_qml(Path("Pages") / "Header" / "TopTabBar.qml")
    top_status = read_qml(Path("Pages") / "Header" / "TopMsg.qml")
    title = read_qml(
        Path("Pages") / "Header" / "WindowTitleLabel.qml"
    )

    for dependency in ("authManager", "globalContext"):
        assert f"required property var {dependency}" in main_layout
        assert f"required property var {dependency}" in top_header
    for dependency in ("adaptiveMetrics", "modelStore", "authManager"):
        assert f"required property var {dependency}" in coil_tools
    assert "coreStyle." not in top_header
    assert "adaptive." not in top_header
    assert "auth." not in top_header
    assert "global." not in top_header
    assert "coreModel." not in coil_tools
    assert "adaptive." not in coil_tools
    assert "auth." not in coil_tools
    assert "root.modelStore.quickLyImage = quickToggle.checked" in coil_tools
    assert "= quickLyImage" not in coil_tools
    for component in (top_tools, top_tabs, top_status, title):
        assert "required property var" in component
    assert "popManage." not in top_tools
    assert "app_core." not in top_tabs
    assert "coreModel." not in top_status
    assert "core." not in top_status
    assert "core." not in title
    assert "control." not in title
    generic_title = read_qml(
        Path("Pages") / "Header" / "TitleLabel.qml"
    )
    assert "DragHandler" not in generic_title
    assert "TapHandler" not in generic_title


def test_style_menu_and_color_picker_are_explicit_and_self_contained():
    style_menu = read_qml(Path("Style") / "StyleMenu.qml")
    color_item = read_qml(
        Path("Controls") / "Menu" / "TextColorMenuItem.qml"
    )
    select_item = read_qml(
        Path("Controls") / "Menu" / "SelectMenuItem.qml"
    )

    for dependency in (
        "style",
        "settings",
        "popupManager",
        "authManager",
        "graphsManager",
        "deviceCurveManager",
    ):
        assert f"required property var {dependency}" in style_menu
    assert "coreStyle." not in style_menu
    assert "coreSetting." not in style_menu
    assert "popManage." not in style_menu
    assert "colorFunc" not in style_menu
    assert "ColorDialog {" in color_item
    assert "colorFunc" not in color_item
    assert "property var style" in select_item
    assert "coreStyle." not in select_item


def test_device_curve_requests_are_stable_and_table_rows_are_reusable():
    app_text = read_qml(Path("App.qml"))
    curve_path = (
        Path("Graphs") / "DeviceCurveView" / "DeviceCurveViewMain.qml"
    )
    row_path = (
        Path("Graphs") / "DeviceCurveView" / "DeviceCurveTableRow.qml"
    )
    curve_text = read_qml(curve_path)
    row_text = read_qml(row_path)
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")

    for dependency in ("apiClient", "modelStore", "style"):
        assert f"required property var {dependency}" in curve_text
        assert f"{dependency}: app." in app_text
    assert "property int requestGeneration: 0" in curve_text
    assert "property bool loading: false" in curve_text
    assert "generation !== root.requestGeneration" in curve_text
    assert "JsonUtils.parse(" in curve_text
    assert "JSON.parse(" not in curve_text
    assert "delegate: DeviceCurveTableRow {" in curve_text
    assert "required property var style" in row_text
    assert row_text.count("required property var ") >= 13
    assert "style.selectionColor" in row_text
    assert f"<file>qml/{row_path.as_posix()}</file>" in qrc_text


def test_camera_adjustment_actions_do_not_race_periodic_refresh():
    settings_view = read_qml(Path("SettingPage") / "SettingPageView.qml")
    camera_path = (
        Path("SettingPage") / "CameraSetting" / "CameraSetting.qml"
    )
    row_path = (
        Path("SettingPage")
        / "CameraSetting"
        / "CameraAdjustmentRow.qml"
    )
    camera_text = read_qml(camera_path)
    row_text = read_qml(row_path)
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")

    for dependency in ("apiClient", "style"):
        assert f"required property var {dependency}" in camera_text
        assert f"{dependency}: root.{dependency}" in settings_view
    assert "property int actionCount: 0" in camera_text
    assert "property int requestGeneration: 0" in camera_text
    assert "readonly property bool busy: loading || actionCount > 0" in camera_text
    assert "if (root.busy)" in camera_text
    assert "generation !== root.requestGeneration" in camera_text
    assert "function finishAction(index, cameraKey)" in camera_text
    assert "cameraModel.get(index).key === cameraKey" in camera_text
    assert "delegate: CameraAdjustmentRow {" in camera_text
    assert "app.api" not in camera_text
    assert "required property var model" in row_text
    assert "required property int index" in row_text
    assert "style.statusSuccessColor" in row_text
    assert "style.statusWarningColor" in row_text
    assert "style.statusErrorColor" in row_text
    assert f"<file>qml/{row_path.as_posix()}</file>" in qrc_text


def test_taper_summary_reuses_surface_rows_and_avoids_cross_component_ids():
    app_text = read_qml(Path("App.qml"))
    main_layout = read_qml(Path("MainLayout.qml"))
    left_popup = read_qml(Path("Pages") / "Pop" / "LeftPrePop.qml")
    table_path = Path("Pages") / "Pop" / "TaperShapeTable.qml"
    row_path = Path("Pages") / "Pop" / "TaperShapeRow.qml"
    cell_path = Path("Pages") / "Pop" / "TaperPointCell.qml"
    table_text = read_qml(table_path)
    row_text = read_qml(row_path)
    cell_text = read_qml(cell_path)
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")

    assert len(table_text.splitlines()) < 100
    assert table_text.count("TaperShapeRow {") == 2
    assert "required property var style" in table_text
    assert "childrenAlarmTaperShape" in table_text
    assert "Material.color" not in table_text
    assert "required property var data" in row_text
    assert row_text.count("TaperPointCell {") == 4
    assert "required property string valueKey" in cell_text
    assert cell_text.count("width: root.width") == 3
    assert "width: parent.width" not in cell_text
    assert "style.statusErrorColor" in cell_text
    assert "style.statusSuccessColor" in cell_text
    assert "x: left.width" not in left_popup
    assert "root.style.leftWidth" in left_popup
    assert "hoverController: root.leftController" in main_layout
    assert "leftController: app.leftCore" in app_text
    for resource_path in (row_path, cell_path):
        assert f"<file>qml/{resource_path.as_posix()}</file>" in qrc_text


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
    assert re.search(
        r"activeApiPort:\s*root\.settings\.useRustTestServer\s*\?\s*rustApiPort\s*:\s*pythonApiPort",
        api_config_text,
    )
    assert re.search(
        r"activeImageServerPort:\s*root\.settings\.useRustImageServer\s*"
        r"\?\s*rustImageServerPort\s*:\s*pythonImageServerPort",
        api_config_text,
    )
    for dependency in ("settings", "style"):
        assert f"required property var {dependency}" in general_setting_text
    assert "coreSetting." not in general_setting_text
    assert "coreStyle." not in general_setting_text
    assert "onValueModified: root.settings.defaultAreaTileCount" in general_setting_text
    assert "onValueChanged: coreSetting.defaultAreaTileCount" not in general_setting_text
    assert "active: api_database.settings.useRustTestServer" in api_database_text
    assert "if (!api_database.settings.useRustTestServer)" in api_database_text
    assert "server_port" not in connect_dialog_text
    assert "rustImageServerPort" not in general_setting_text


def test_infinite_alert_animations_stop_when_their_visual_is_hidden():
    label_text = read_qml(Path("animation") / "AnimLabel.qml")
    image_text = read_qml(Path("animation") / "AnimErrorImage.qml")
    error_label_text = read_qml(Path("animation") / "AnimErrorLabel.qml")
    simple_error_path = (
        QML_ROOT / "Pages" / "AlarmPage" / "AlarmSimple" / "SimpleErrView.qml"
    )

    for text in (label_text, image_text):
        assert "SequentialAnimation {" in text
        assert "loops: Animation.Infinite" in text
        assert "running: root.running && root.visible" in text
        assert "onFinished:" not in text
        assert "restart()" not in text
    assert "running: root.running && root.visible" in error_label_text
    assert not simple_error_path.exists()


def test_header_time_text_is_readable_on_dark_theme():
    time_text = read_qml(Path("Base") / "TimeText.qml")

    assert 'color: "#333"' not in time_text
    assert "color: root.style.titleColor" in time_text


def test_height_point_websocket_reconnects_after_close():
    api_text = read_qml(Path("Api") / "Api_DataBase.qml")

    assert "Timer {" in api_text
    assert "id: heightPointReconnectTimer" in api_text
    assert "function _scheduleHeightPointReconnect()" in api_text
    assert re.search(
        r"active:\s*api_database\.settings\.useRustTestServer\s*"
        r"&&\s*api_database\._heightPointConnectEnabled",
        api_text,
    )
    assert "heightPointSocket.active =" not in api_text
    assert "_heightPointReconnectDelayMs * 2" in api_text
    assert "_heightPointReconnectMaxDelayMs" in api_text
    assert "_scheduleHeightPointReconnect()" in api_text


def test_area_tiles_use_column_for_x_and_row_for_y():
    view_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageView.qml")
    item_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageItem.qml")

    assert "x: parseInt(index % root.count_) * width" in view_text
    assert "y: parseInt(index / root.count_) * height" in view_text
    assert "row_: parseInt(index/root.count_)" in view_text
    assert "col_: parseInt(index%root.count_)" in view_text
    assert "property url targetSource" in item_text
    assert "var nextSource = buildImageUrl(targetLevel)" in item_text
    assert "if (targetSource !== nextSource)" in item_text


def test_area_low_resolution_levels_load_the_complete_grid():
    view_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageView.qml")
    item_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageItem.qml")

    assert "readonly property bool loadCompleteGrid: enableParallelLoad || currentLevel <= 1" in view_text
    assert "enableParallelLoad: root.loadCompleteGrid" in view_text
    assert "readonly property bool shouldLoad: enableParallelLoad || isInViewport" in item_text
    assert "onCurrentLevelChanged: updateLevel(currentLevel)" in item_text


def test_area_tiles_keep_only_preview_and_current_quality_images():
    item_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageItem.qml")

    assert item_text.count("Image {") == 2
    assert "id: previewImage" in item_text
    assert "id: targetImage" in item_text
    assert "levelImage0" not in item_text
    assert "levelSource0" not in item_text
    assert "function unloadHighResolution()" in item_text
    assert "if (!enableParallelLoad && targetLevel >= 2)" in item_text
    assert "onShouldLoadChanged:" in item_text
    assert item_text.count("onImageUrlChanged:") == 1
    assert item_text.count("onPreviewUrlChanged:") == 1
    assert "settings: root.settings" in read_qml(
        Path("Controls") / "TiledImageView" / "TiledImageView.qml"
    )
    assert "style: root.style" in read_qml(
        Path("Controls") / "TiledImageView" / "TiledImageView.qml"
    )
    assert "root.style.viewportBackgroundColor" in item_text


def test_area_tile_quality_is_signal_driven_instead_of_polled():
    view_text = read_qml(Path("Controls") / "TiledImageView" / "TiledImageView.qml")
    image_text = read_qml(Path("DataShow") / "ViewArea" / "ImageView.qml")

    for dependency in ("controller", "apiClient", "settings", "surface", "style"):
        assert f"required property var {dependency}" in view_text
        assert f"{dependency}:" in image_text
    assert "function onCanvasScaleChanged()" in view_text
    assert "scaleEvaluationTimer.restart()" in view_text
    assert "id: scaleEvaluationTimer" in view_text
    assert "repeat: false" in view_text
    assert "scaleCheckTimer" not in view_text
    assert "repeat: true\n        running: enableMultiLevel" not in view_text
    assert "_requestToken += 1" in view_text
    assert "Invalid image info" in view_text
    assert "function updateAllTiles()" not in view_text
    assert ".itemAt(" not in view_text
    assert "tileRefreshGeneration += 1" in view_text
    assert "onRefreshGenerationChanged: updateLevel(currentLevel)" in read_qml(
        Path("Controls") / "TiledImageView" / "TiledImageItem.qml"
    )


def test_image_preload_cache_is_bounded_deduplicated_and_releases_when_disabled():
    cache_text = read_qml(Path("Core") / "ImageCache.qml")
    app_text = read_qml(Path("App.qml"))

    assert "required property var settings" in cache_text
    assert "Math.max(0, Number(settings.maxImageCache) || 0)" in cache_text
    assert "function indexOfSource(source)" in cache_text
    assert "if (existingIndex >= 0)" in cache_text
    assert "while (cacheModel.count >= maxCache)" in cache_text
    assert "cacheModel.clear()" in cache_text
    assert "onCacheEnabledChanged: trimCache()" in cache_text
    assert "onMaxCacheChanged: trimCache()" in cache_text
    assert "visible: false" in cache_text
    assert "settings: app.coreSetting" in app_text
    assert "cacheAbel" not in cache_text


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
    assert "root.apiClient.clearRustImageCache" in area_core_text
    assert "areaCacheVersion += 1" in area_core_text
    assert "function recacheAreaTiles()" in area_core_text
    assert "canRecacheAreaTiles" in menu_text
    assert "root.controller.recacheAreaTiles()" in menu_text
    assert "重新缓存 2D 图像" in menu_text


def test_2d_defects_share_defect_class_visibility_list():
    defect_class_text = read_qml(Path("Property") / "DefectClassProperty.qml")
    data_show_core_text = read_qml(Path("DataShow") / "Core" / "_base_" / "DataShowCore_.qml")
    filter_core_text = read_qml(Path("DefectPage") / "Core" / "FilterCore.qml")

    assert "function shared_defect_name(defectName)" in defect_class_text
    assert "return name.slice(3)" in defect_class_text
    assert "function normalize_defect_dict_data(data)" in defect_class_text
    assert 'if (sharedName in normalized)' in defect_class_text
    assert "root.globalContext.defectClassProperty.shared_defect_name(" in data_show_core_text
    assert (
        "let sharedName = root.globalContext.defectClassProperty.shared_defect_name(name)"
        in filter_core_text
    )


def test_coil_list_max_defect_excludes_masked_classes():
    defect_class_text = read_qml(Path("Property") / "DefectClassProperty.qml")
    coil_model_text = read_qml(Path("Model") / "CoilModel.qml")

    assert "signal defectConfigurationChanged()" in defect_class_text
    assert "function is_defect_enabled(defectName)" in defect_class_text
    assert "return initialized ? defaultDefectClass.defectShow : true" in defect_class_text
    assert "function onDefectConfigurationChanged()" in coil_model_text
    assert (
        "defectClassProperty.is_defect_enabled(configName)"
        in coil_model_text
    )
    assert 'maxDefectName = ""' in coil_model_text
    assert "maxDefectLevel = 0" in coil_model_text
    assert 'maxDefectSurface = ""' in coil_model_text


def test_pending_defect_is_consumed_only_by_the_matching_view():
    menu_text = read_qml(Path("DefectPage") / "DfectView" / "DefectDataViewMenu.qml")
    image_core_text = read_qml(Path("DataShow") / "Core" / "DataShowCore.qml")
    area_core_text = read_qml(Path("DataShow") / "Core" / "DataShowAreaCore.qml")

    assert 'viewMode: "2D"' in menu_text
    assert "&& !root.surfaceData.isAreaRootView" in image_core_text
    assert 'let targetView = pending.viewMode || "2D"' in image_core_text
    assert 'targetView !== "AREA"' in image_core_text
    assert "&& root.surfaceData.isAreaRootView" in area_core_text
    assert 'let targetView = pending.viewMode || "AREA"' in area_core_text
    assert 'targetView === "AREA"' in area_core_text
    for text in (image_core_text, area_core_text):
        assert "&& setDefectShowView(pending)" in text
        assert "root.modelStore.pendingDefect = null" in text


def test_image_viewports_share_bounded_zoom_and_throttled_pointer_updates():
    zoom_text = read_qml(Path("DataShow") / "Core" / "ViewportMath.js")
    image_control_text = read_qml(Path("DataShow") / "2dShow" / "ControlView.qml")
    area_control_text = read_qml(Path("DataShow") / "ViewArea" / "ControlView.qml")
    image_view_text = read_qml(Path("DataShow") / "2dShow" / "Show2dView.qml")
    area_core_text = read_qml(Path("DataShow") / "Core" / "DataShowAreaCore.qml")

    assert "function zoomAt(controller, flickable, eventX, eventY, wheelDelta)" in zoom_text
    assert "var targetScale = clamp(" in zoom_text
    assert "controller.setFlickablebyPoint(viewportPoint)" in zoom_text
    for text in (image_control_text, area_control_text):
        assert 'import "../Core/ViewportMath.js" as ViewportMath' in text
        assert "ViewportMath.zoomAt(" in text
        assert "canvasScale *= 1.1" not in text
        assert "canvasScale *= 0.9" not in text
    assert "Math.abs(dataShowCore.hoverPoint.x-point.position.x>5)" not in image_view_text
    assert "root.dataShowCore.hoverPoint.x - point.position.x" in image_view_text
    assert "if (deltaX < 2 && deltaY < 2)" in image_view_text
    assert "root.dataShowCore.chartHovered" in image_view_text
    assert "root.dataShowCore.imageShowHovered" in image_view_text
    assert "required property var surfaceData" in area_core_text


def test_2d_image_loading_uses_valid_thumbnail_urls_and_independent_alarm_overlay():
    image_text = read_qml(Path("DataShow") / "2dShow" / "ImageView.qml")

    assert 'return url + (url.indexOf("?") >= 0 ? "&" : "?") + query' in image_text
    assert 'root.appendQuery(root.surfaceData.source,' in image_text
    assert '"thumbnail=true")' in image_text
    assert "source: thumbnailBaseUrl" in image_text
    assert 'surfaceData.source + "&thumbnail=true"' not in image_text
    assert "visible: root.surfaceData.error_visible" in image_text
    assert "surfaceData.error_visible && dataShowCore.adjustConfig.image_gamma_enable" not in image_text
    assert "running: fullImage.status === Image.Loading" in image_text
    assert 'text: qsTr("图像加载失败")' in image_text


def test_coil_list_reuses_delegates_and_maps_filtered_selection_by_id():
    list_view_text = read_qml(Path("Pages") / "LeftPage" / "DataList" / "DataListView.qml")
    delegate_text = read_qml(Path("Pages") / "LeftPage" / "DataList" / "DataListViewItenBase.qml")
    animation_text = read_qml(Path("animation") / "AnimListView.qml")
    left_core_text = read_qml(Path("Core") / "LefeCore.qml")
    status_text = read_qml(
        Path("Pages") / "LeftPage" / "DataList" / "StatusMsg.qml"
    )

    assert "reuseItems: true" in animation_text
    assert "cacheBuffer: Math.max(240, height)" in animation_text
    assert "duration: 140" in animation_text
    assert "duration: 1000" not in animation_text
    assert "ListView.onReused: syncModel()" in delegate_text
    assert "root.leftController.selectVisibleIndex(root.index)" in delegate_text
    assert "required property int index" in delegate_text
    assert "required property var model" in delegate_text
    assert "onCurrentIndexChanged" not in list_view_text
    for dependency in (
        "style",
        "coreController",
        "modelController",
        "leftController",
        "popupManager",
    ):
        assert f"required property var {dependency}" in list_view_text
    assert "leftCore." not in list_view_text
    assert "coreModel." not in list_view_text
    assert "popManage." not in list_view_text
    assert "root.leftController.visibleIndexForCoilId(" in list_view_text
    assert "required property var coilModel" in status_text
    assert "required property var summary" in status_text
    assert "listItemCoil." not in status_text
    assert "function indexForCoilId(model, coilId)" in left_core_text
    assert "function selectVisibleIndex(index)" in left_core_text
    assert (
        "root.indexForCoilId(root.modelStore.currentCoilListModel, coilId)"
        in left_core_text
    )
    assert "item_data.childrenCoilDefect || item_data.defects || []" in left_core_text


def test_coil_alarm_summary_handles_missing_data_and_uses_semantic_colors():
    alarm_text = read_qml(
        Path("Pages") / "LeftPage" / "DataList" / "Core" / "AlarmInfoItem.qml"
    )
    summary_text = read_qml(
        Path("Pages") / "LeftPage" / "DataList" / "Core" / "ListItemCoil.qml"
    )

    assert "var source = value || {}" in alarm_text
    assert "Component.onCompleted: applyData(data)" in alarm_text
    assert "Boolean(alarmInfo && (alarmInfo.S || alarmInfo.L))" in summary_text
    assert "root.alarmInfo && root.alarmInfo.S ? root.alarmInfo.S : null" in summary_text
    assert 'return level > 1 ? style.getIcon("warning_1") : ""' in summary_text
    assert "property ListModel alarmNodel" not in summary_text
    assert "required property var style" in summary_text
    for token in ("statusSuccessColor", "statusWarningColor", "statusErrorColor"):
        assert f"style.{token}" in summary_text


def test_defect_grid_uses_native_virtualization_and_reusable_delegates():
    grid_text = read_qml(Path("DefectPage") / "DfectView" / "DefectDataView.qml")
    item_text = read_qml(Path("DefectPage") / "DfectView" / "DefectItemShow.qml")

    assert "ScrollView {" not in grid_text
    assert "GridView {" in grid_text
    assert "reuseItems: true" in grid_text
    assert "cacheBuffer: cellHeight * 2" in grid_text
    assert "delegate: DefectItemShow {" in grid_text
    assert "delegate:Loader" not in grid_text
    assert "required property int index" in item_text
    assert "required property var model" in item_text
    assert "GridView.onReused: syncModel()" in item_text
    assert "defectItem.init(model)" in item_text
    assert "cache: false" in item_text
    assert "ToolTip.visible: hovered" in item_text
    assert "duration: 120" in item_text
    assert "duration: 450" not in item_text


def test_defect_range_refresh_queues_changes_and_rejects_stale_responses():
    control_text = read_qml(Path("DefectPage") / "Core" / "ControlCore.qml")

    assert "property bool refreshQueued: false" in control_text
    assert "property int requestGeneration: 0" in control_text
    assert "if (root.loading) {" in control_text
    assert "root.refreshQueued = true" in control_text
    assert "if (generation !== root.requestGeneration)" in control_text
    assert "Qt.callLater(root.flushDefects)" in control_text
    assert "function forceRefresh()" in control_text
    assert "defect response parse failed" in control_text


def test_hovered_coil_details_parse_json_and_use_bounded_request_cache():
    left_core_text = read_qml(Path("Core") / "LefeCore.qml")

    assert "property int detailCacheMax: 80" in left_core_text
    assert "property var pendingDetailRequests: ({})" in left_core_text
    assert "function cachedDetail(coilId)" in left_core_text
    assert "function cacheDetail(coilId, data)" in left_core_text
    assert "while (order.length > root.detailCacheMax)" in left_core_text
    assert 'if (typeof data !== "string")' in left_core_text
    assert "return JSON.parse(data)" in left_core_text
    assert (
        "root.pendingDetailRequests[requestKey] = root.apiClient.getCoilDetail"
        in left_core_text
    )
    assert "delete root.pendingDetailRequests[requestKey]" in left_core_text
    assert "pendingDetailCoilId" not in left_core_text


def test_clock_is_shared_and_unused_duplicate_datetime_components_are_removed():
    time_text = read_qml(Path("Base") / "TimeText.qml")
    core_text = read_qml(Path("Core") / "Core.qml")
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")

    assert "Timer {" not in time_text
    assert "required property var coreController" in time_text
    assert "root.coreController.nowTime" in time_text
    assert 'Qt.formatDateTime(root.currentDate, "yyyy-MM-dd HH:mm:ss")' in time_text
    assert "triggeredOnStart: true" in core_text
    assert "root.appWindow.visibility !== Window.Minimized" in core_text
    for removed_path in (
        Path("Base") / "DateTime.qml",
        Path("Base") / "NowDate.qml",
        Path("Comp") / "DateTime.qml",
        Path("Comp") / "DateTimeLab.qml",
        Path("Comp") / "NowDate.qml",
        Path("Labels") / "DateTimeLab.qml",
    ):
        assert not (QML_ROOT / removed_path).exists()
        assert f"qml/{removed_path.as_posix()}" not in qrc_text


def test_unreferenced_legacy_and_broken_demo_components_are_removed():
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")
    removed_paths = (
        Path("Base") / "ScrollBarBase2.qml",
        Path("btns") / "MoreSet.qml",
        Path("Comp") / "Images" / "AlarmColorImage.qml",
        Path("DefectPage") / "CardView" / "AlarmSetting" / "AlarmSettingView.qml",
        Path("DefectPage")
        / "CardView"
        / "AlarmSetting"
        / "AlarmSettingViewButtons.qml",
        Path("Graphs") / "Test" / "GraphsTest.qml",
        Path("Pages") / "States" / "StatesView.qml",
        Path("ScreenView.qml"),
        Path("Base") / "DefectDraw.qml",
        Path("Base") / "DefectView.qml",
        Path("Base") / "SelectCursor.qml",
        Path("Base") / "SelectItemInfoView.qml",
        Path("Comp")
        / "SimpleList"
        / "SimpleListView2250"
        / "ListItemDelegate2250.qml",
        Path("Comp")
        / "SimpleList"
        / "SimpleListView2250"
        / "SimpleListView2250.qml",
        Path("DataShow") / "DataShowMsg" / "DataShowLabelsViewAll.qml",
    )

    for removed_path in removed_paths:
        assert not (QML_ROOT / removed_path).exists()
        assert f"qml/{removed_path.as_posix()}" not in qrc_text


def test_unused_area_draw_copy_is_removed_and_active_overlay_is_safe():
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")
    view_area_text = read_qml(
        Path("DataShow") / "ViewArea" / "ViewArea.qml"
    )
    active_draw = read_qml(
        Path("DataShow") / "2dShow" / "Draw" / "DrawView.qml"
    )
    removed_draw_root = (
        QML_ROOT / "DataShow" / "ViewArea" / "Draw"
    )

    assert not list(removed_draw_root.rglob("*.qml"))
    assert "qml/DataShow/ViewArea/Draw/" not in qrc_text
    assert 'import "Draw"' not in view_area_text
    for dependency in ("surfaceData", "dataShowCore", "style", "apiClient"):
        assert f"required property var {dependency}" in active_draw
    assert "source && source.length > 1 && source[1]" in active_draw
    assert "function requestCanvasPaint()" in active_draw
    assert "function onCanvasScaleChanged()" in active_draw
    assert "function onCountChanged()" in active_draw
    assert "root.perpendicularPoint !== undefined" in active_draw
    assert "isFinite(root.perpendicularPoint.x)" in active_draw
    assert "style.statusSuccessColor" in active_draw
    assert "style.statusErrorColor" in active_draw
    assert "Repeater" not in active_draw


def test_point_overlay_has_explicit_dependencies_and_safe_empty_geometry():
    draw_point = read_qml(
        Path("DataShow") / "2dShow" / "Draw" / "DrawPoint.qml"
    )
    point_root = (
        Path("DataShow") / "2dShow" / "Draw" / "PointShow"
    )
    db_points = read_qml(point_root / "DbPointShow.qml")
    user_points = read_qml(point_root / "UserPointShow.qml")
    point_item = read_qml(point_root / "PointItem.qml")
    point_view = read_qml(point_root / "PointViewItem.qml")

    for dependency in (
        "surfaceData",
        "dataShowCore",
        "style",
        "apiClient",
        "innerEllipse",
    ):
        assert f"required property var {dependency}" in draw_point
    assert "required property var innerEllipse" in db_points
    assert "inner_ellipse" not in db_points
    assert "if (distance === 0)" in db_points
    assert "return Qt.point(px, py)" in db_points
    assert "pragma ComponentBehavior: Bound" in db_points
    assert "pragma ComponentBehavior: Bound" in user_points
    assert "required property var pointProjector" in point_item
    for dependency in ("apiClient", "surfaceData", "dataShowCore", "style"):
        assert f"required property var {dependency}" in point_view
    assert "api." not in point_view
    assert "coreStyle." not in point_view


def test_search_filter_uses_valid_explicit_spacing_metric():
    search_view = read_qml(
        Path("Pages") / "LeftPage" / "SearchView" / "SearchView.qml"
    )
    filter_view = read_qml(
        Path("Pages") / "LeftPage" / "SearchView" / "FilterView.qml"
    )

    for dependency in ("adaptiveMetrics", "style"):
        assert f"required property var {dependency}" in search_view
        assert f"required property var {dependency}" in filter_view
    assert "required property var leftController" in search_view
    assert "spacing: root.style.headerButtonGap" in filter_view
    assert "adaptive.headerButtonGap" not in filter_view
    assert "app.coreStyle" not in filter_view


def test_global_error_levels_are_event_driven_instead_of_polled():
    error_text = read_qml(Path("Core") / "CoreGlobalError.qml")
    net_text = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmItemNet.qml"
    )

    assert "Timer {" not in error_text
    assert "function setStateLevel(group, key, level)" in error_text
    assert "errorState = Object.assign({}, state)" in error_text
    assert "function refreshPrimaryError()" in error_text
    assert "errorDict = Object.assign({}, errors)" in error_text
    assert "root.modelStore.coreGlobalError.setStateLevel(" in net_text
    assert '"网络", i, ok ? 0 : 3)' in net_text
    assert 'errorState["网络"][i]' not in net_text


def test_api_payloads_use_shared_safe_json_parser_on_runtime_paths():
    json_utils = read_qml(Path("Core") / "JsonUtils.js")
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")
    guarded_paths = (
        Path("Core") / "CoreControl.qml",
        Path("Core") / "CoreModel.qml",
        Path("Core") / "CaptureAlarmWatcher.qml",
        Path("Core") / "Surface" / "SurfaceData.qml",
        Path("DataShow") / "Core" / "_base_" / "DataShowCore_.qml",
        Path("DefectPage") / "Head" / "HeadToolBox.qml",
        Path("Pages") / "AlarmPage" / "CoreAlarmInfo.qml",
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmHardware.qml",
        Path("Pages") / "AlarmPage" / "AlarmCheckInfo" / "AlarmCheckInfoView.qml",
        Path("PopupView") / "MsgPop" / "MsgPopView.qml",
        Path("SettingPage") / "CameraSetting" / "CameraSetting.qml",
        Path("PopupView") / "HardwareMonitor" / "HardwareMonitorView.qml",
        Path("PopupView") / "AlgTest" / "AlgTestDialog.qml",
        Path("SettingPage") / "OtherSetting" / "SoftwareUpdate.qml",
    )

    assert ".pragma library" in json_utils
    assert "function parse(value, fallbackValue, context)" in json_utils
    assert "try {" in json_utils
    assert "catch (error)" in json_utils
    assert "<file>qml/Core/JsonUtils.js</file>" in qrc_text
    for relative_path in guarded_paths:
        text = read_qml(relative_path)
        assert "JsonUtils.js" in text
        assert "JsonUtils.parse(" in text


def test_coil_specific_requests_reject_stale_responses_and_debug_payloads_are_removed():
    alarm_text = read_qml(Path("Pages") / "AlarmPage" / "CoreAlarmInfo.qml")
    status_text = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmCheckInfo" / "AlarmCheckInfoView.qml"
    )
    detail_text = read_qml(Path("PopupView") / "MsgPop" / "MsgPopView.qml")

    assert "property int requestGeneration: 0" in alarm_text
    assert "requestedCoilId !== root.coilId" in alarm_text
    assert "property int statusRequestGeneration: 0" in status_text
    assert "requestedCoilId !== root.coilId" in status_text
    assert "property int detailsRequestGeneration: 0" in detail_text
    assert detail_text.count("requestedCoilId !== menu.currentCoilId") >= 2
    assert "property string currentCoilNo" not in detail_text
    assert "datetime.datetime(" not in detail_text
    assert "var t = [" not in detail_text
    for token in (
        "root.style.statusSuccessColor",
        "root.style.statusWarningColor",
        "root.style.statusErrorColor",
    ):
        assert token in alarm_text


def test_network_alarm_probes_real_service_ports_without_legacy_duplicates():
    net_text = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmItemNet.qml"
    )

    assert 'titleText: "核心 API"' in net_text
    assert 'titleText: "图像服务"' in net_text
    assert 'titleText: "2D 算法"' in net_text
    assert "root.apiClient.apiConfig.activeApiPort" in net_text
    assert "root.apiClient.apiConfig.activeImageServerPort" in net_text
    assert "root.apiClient.apiConfig.alg2dPort" in net_text
    assert "api.apiConfig.databasPort" not in net_text
    assert "api.apiConfig.dataPort" not in net_text


def test_capture_alarm_polling_uses_explicit_dependencies_and_stops_offline():
    watcher_text = read_qml(Path("Core") / "CaptureAlarmWatcher.qml")
    app_text = read_qml(Path("App.qml"))
    camera_text = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmItemCameras.qml"
    )
    global_alarm_text = read_qml(
        Path("PopupView") / "GlobalAlarm" / "GlobalAlarmView.qml"
    )
    qrc_text = (MOTION_STUDIO_ROOT / "qml.qrc").read_text(encoding="utf-8")

    for dependency in ("apiClient", "errorController", "connectionState"):
        assert f"required property var {dependency}" in watcher_text
        assert f"{dependency}: app." in app_text
    assert "running: root.connectionState.connected" in watcher_text
    assert "requestRunning || !connectionState.connected" in watcher_text
    assert "app.api" not in watcher_text
    assert "app.coreModel" not in watcher_text
    assert "property var statusPayload" in watcher_text
    assert "statusPayload = Object.assign({}, payload)" in watcher_text
    assert "Timer {" not in camera_text
    assert "getCameraAlarm" not in camera_text
    assert "onStatusPayloadChanged" in camera_text
    assert "reuseItems: true" in camera_text
    assert "watcher: root.captureAlarmWatcher" in global_alarm_text
    assert "AlarmInfoGlob.qml" not in qrc_text


def test_alarm_grid_delegates_use_required_roles_and_semantic_status_colors():
    camera_item = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmItemCamerasItem.qml"
    )
    camera_view = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmItemCameras.qml"
    )
    hardware_item = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmItemHardwareItem.qml"
    )
    net_item = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmItemNetItem.qml"
    )
    hardware_view = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmHardware.qml"
    )
    net_view = read_qml(
        Path("Pages") / "AlarmPage" / "AlarmItem" / "AlarmItemNet.qml"
    )

    for text in (camera_item, hardware_item, net_item):
        assert "required property" in text
        assert "required property var style" in text
        assert "style.statusErrorColor" in text
        assert "style.statusSuccessColor" in text
    assert "style.statusWarningColor" in hardware_item
    assert 'required property string cameraKey' in camera_item
    assert '"cameraKey": key' in camera_view
    assert 'required property string Key' not in camera_item
    assert "reuseItems: true" in hardware_view
    assert "reuseItems: true" in net_view
    assert "triggeredOnStart: true" in hardware_view
    assert "interval: 5000" in hardware_view


def test_3d_model_loads_immediately_and_retries_with_bounded_backoff():
    node_text = read_qml(Path("DataShow") / "View3D" / "Node3D.qml")

    assert "property int maxReloadAttempts: 3" in node_text
    assert "scheduleModelLoad(1)" in node_text
    assert "root.reloadAttempt - 1" in node_text
    assert "Math.min(" in node_text
    assert "3000," in node_text
    assert "root.reloadAttempt < root.maxReloadAttempts" in node_text
    assert "interval:5000" not in node_text
    assert 'console.log("Model loaded successfully")' not in node_text


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
