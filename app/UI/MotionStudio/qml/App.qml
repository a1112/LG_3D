import QtQuick.Window
import Qt.labs.settings 1.1
import QtQuick
import QtQuick.Controls
import "."

import QtQuick.Controls.Material
import "./Api"
import "./Core"

import "Pages/AlarmPage"
import "Dialogs"
import "./Style/Adaptive"
import "Graphs"
AppBase {
    property QtObject startupGeometry: QtObject {
        property var saved: Settings {
            fileName: typeof startupGeometrySettingsFile === "undefined" ? "" : startupGeometrySettingsFile
            category: "StartupWindowGeometry"
            property int savedX: 0
            property int savedY: 0
            property int savedWidth: 0
            property int savedHeight: 0
        }
        property bool ready: false
        function remember() {
            if (!ready || app.visibility !== Window.Windowed) return
            saved.savedX = app.x; saved.savedY = app.y
            saved.savedWidth = app.width; saved.savedHeight = app.height
        }
        property var initialize: Timer {
            interval: 0; running: true; repeat: false
            onTriggered: {
                const restored = startupGeometry.saved.savedWidth > 0 && startupGeometry.saved.savedHeight > 0
                let screen = app.screen
                if (restored) {
                    const screens = Qt.application.screens
                    for (let i = 0; i < screens.length; ++i) {
                        const candidate = screens[i]
                        if (startupGeometry.saved.savedX >= candidate.virtualX && startupGeometry.saved.savedX < candidate.virtualX + candidate.width && startupGeometry.saved.savedY >= candidate.virtualY && startupGeometry.saved.savedY < candidate.virtualY + candidate.height) { screen = candidate; break }
                    }
                    app.screen = screen
                }
                let area = {x: screen.virtualX, y: screen.virtualY + 32, width: Math.min(screen.width, screen.desktopAvailableWidth), height: Math.min(screen.height, screen.desktopAvailableHeight) - 64}
                if (typeof startupWorkAreas !== "undefined") {
                    for (let i = 0; i < startupWorkAreas.length; ++i) {
                        if (startupWorkAreas[i].screenX === screen.virtualX && startupWorkAreas[i].screenY === screen.virtualY) { area = startupWorkAreas[i]; break }
                    }
                }
                const aw = area.width, ah = area.height
                const maxW = Math.max(1, aw - 64), maxH = Math.max(1, ah - 96)
                const nominalMinimumW = Math.min(960, maxW)
                const nominalMinimumH = Math.min(600, maxH)
                const width = restored ? startupGeometry.saved.savedWidth : Math.min(1240, aw * 0.82)
                const height = restored ? startupGeometry.saved.savedHeight : Math.min(800, ah * 0.84)
                const sx = area.x, sy = area.y
                const frame = typeof startupWindowFrame === "undefined" ? {left:0, top:0, right:0, bottom:0} : startupWindowFrame
                const rawW = Math.max(1, aw - frame.left - frame.right)
                const rawH = Math.max(1, ah - frame.top - frame.bottom)
                const fittedW = restored && width <= rawW ? width : Math.min(width, maxW)
                const fittedH = restored && height <= rawH ? height : Math.min(height, maxH)
                app.minimumWidth = Math.min(nominalMinimumW, fittedW)
                app.minimumHeight = Math.min(nominalMinimumH, fittedH)
                app.width = Math.max(app.minimumWidth, fittedW)
                app.height = Math.max(app.minimumHeight, fittedH)
                app.x = restored ? Math.max(sx + frame.left, Math.min(startupGeometry.saved.savedX, sx + aw - app.width - frame.right)) : sx + (aw - app.width + frame.left - frame.right) / 2
                app.y = restored ? Math.max(sy + frame.top, Math.min(startupGeometry.saved.savedY, sy + ah - app.height - frame.bottom)) : sy + (ah - app.height + frame.top - frame.bottom) / 2
                app.visibility = app.startupRequestedVisibility
                startupGeometry.ready = true
            }
        }
        property var changes: Connections {
            target: app
            function onStartupRequestedVisibilityChanged() {
                if (startupGeometry.ready) app.visibility = app.startupRequestedVisibility
            }
            function onXChanged() { startupGeometry.remember() }
            function onYChanged() { startupGeometry.remember() }
            function onWidthChanged() { startupGeometry.remember() }
            function onHeightChanged() { startupGeometry.remember() }
            function onClosing() { startupGeometry.remember() }
        }
    }

    id: app
    apiClient: app.api
    adaptiveMetrics: app.adaptive
    appStyle: app.coreStyle
    settingsStore: app.coreSetting
    appInfo: app.coreInfo
    downloadClient: fileDownloader
    authManager: app.auth
    graphsManager: app.graphs_manage
    deviceCurveManager: app.device_curve_manage
    modelStore: app.coreModel
    clipboardService: app.cpp.clipboard
    toolService: app.tool
    globalContext: app.global
    dialogManager: app.dialogs
    coreController: app.core
    scriptLauncher: ScriptLauncher
    visibility: Window.Hidden
    property int startupRequestedVisibility: control.visibility

    onVisibilityChanged: function(visibility) {
        if (visibility !== Window.Hidden && control && control.visibility !== visibility) {
            control.visibility = visibility
        }
    }
    Material.theme: coreStyle.theme
    Material.background: coreStyle.panelBackgroundColor
    readonly property int availableWindowWidth: (global.screenConfig.desktopAvailableWidth > 0
        ? global.screenConfig.desktopAvailableWidth : global.screenConfig.width)
    readonly property int availableWindowHeight: (global.screenConfig.desktopAvailableHeight > 0
        ? global.screenConfig.desktopAvailableHeight : global.screenConfig.height)
    width: 1240
    height: 800
    title: qsTr("热轧 3D 端面检测系统") + (coreSetting.testMode ? qsTr(" - [测试模式]") : "")
    color: coreStyle.appBackgroundColor
    Material.accent: coreStyle.accentColor
    CoreAction {
        appWindow: app
    }
    property CppInterFace cpp:CppInterFace{}

    MainLayout{ //    入口,界面构成 <-
        anchors.fill: parent
        adaptiveMetrics: app.adaptive
        style: app.coreStyle
        model: app.coreModel
        settings: app.coreSetting
        viewControl: app.control
        appController: app.app_core
        leftController: app.leftCore
        alarmInfo: app.coreAlarmInfo
        apiClient: app.api
        popupManager: app.popManage
        authManager: app.auth
        globalContext: app.global
        coreController: app.core
        toolService: app.tool
        imageCacheService: app.imageCache
    }

    property CoreAlarmInfo coreAlarmInfo: CoreAlarmInfo {
        coreController: app.core
        apiClient: app.api
        modelStore: app.coreModel
        style: app.coreStyle
    }  // 全局的报警信息
    property Api api: Api{
        connectionState: app.coreState
        errorModel: app.coreModel
        settings: app.coreSetting
        toolService: app.tool
        downloadClient: app.downloadClient
        statusSuccessColor: app.coreStyle.statusSuccessColor
        statusWarningColor: app.coreStyle.statusWarningColor
        statusErrorColor: app.coreStyle.statusErrorColor
    }     //    服务器 接口访问
    property Global global: Global {
        style: app.coreStyle
    }  // 全局功能
    property Dialogs dialogs: Dialogs {
        toolService: app.tool
    } // 全局 弹窗
    property Core core: Core {
        appWindow: app
        settings: app.coreSetting
        apiClient: app.api
        modelStore: app.coreModel
        initController: app.init
        dataController: app.coreControl
        scriptLauncher: app.scriptLauncher
        globalContext: app.global
    }          // 核心
    property Tool tool: Tool{}          // 功能
    property CoreModel coreModel: CoreModel {
        apiClient: app.api
        settings: app.coreSetting
        globalContext: app.global
        coreController: app.core
        initController: app.init
        imageCacheService: app.imageCache
        scriptLauncher: app.scriptLauncher
    }// 全局模型
    property CaptureAlarmWatcher captureAlarmWatcher: CaptureAlarmWatcher {
        apiClient: app.api
        errorController: app.coreModel.coreGlobalError
        connectionState: app.coreState
    }
    property Init init: Init {
        apiClient: app.api
        model: app.coreModel
        coreController: app.core
        globalContext: app.global
        appContext: app
    }               // 初始化
    property CoreStyle coreStyle: CoreStyle{}   // 样式
    property CoreTimer coreTimer: CoreTimer {
        apiClient: app.api
        model: app.coreModel
        settings: app.coreSetting
        initController: app.init
        connectionState: app.coreState
    }     // 定时器
    property CoreSetting coreSetting: CoreSetting{}// 设置
    property ImageCache imageCache: ImageCache {
        settings: app.coreSetting
    } // 缓冲
    property LefeCore leftCore: LefeCore {
        modelStore: app.coreModel
        coreController: app.core
        globalContext: app.global
        toolService: app.tool
        apiClient: app.api
    }  //列表全局
    property Control control: Control {
        authManager: app.auth
    }
    property Auth auth: Auth{}
    property CoreSignal coreSignal: CoreSignal {
        initController: app.init
    }
    property CoreState coreState: CoreState {
        signalController: app.coreSignal
    }
    readonly property AdaptiveViewBase adaptive : coreStyle.currentAdaptive
    property CoreControl coreControl: CoreControl {
        apiClient: app.api
        coreController: app.core
        modelStore: app.coreModel
    }
    property Script autoScript: Script {
        modelStore: app.coreModel
        leftController: app.leftCore
        toolService: app.tool
    }
    // Junp{}
    property AppCore app_core : AppCore{}

    property GraphsManage graphs_manage: GraphsManage{
        modelStore: app.coreModel
    }

    property DeviceCurveManage device_curve_manage: DeviceCurveManage{
        apiClient: app.api
        modelStore: app.coreModel
        style: app.coreStyle
    }

    // 全局运行环境与路径信息
    property CoreInfo coreInfo: CoreInfo{}
}


