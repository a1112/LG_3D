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
    visible: true
    visibility:control.visibility
    onVisibilityChanged: function(visibility) {
        if (control && control.visibility !== visibility) {
            control.visibility = visibility
        }
    }
    Material.theme: coreStyle.theme
    Material.background: coreStyle.panelBackgroundColor
    readonly property int availableWindowWidth: (global.screenConfig.desktopAvailableWidth > 0
        ? global.screenConfig.desktopAvailableWidth : global.screenConfig.width)
    readonly property int availableWindowHeight: (global.screenConfig.desktopAvailableHeight > 0
        ? global.screenConfig.desktopAvailableHeight : global.screenConfig.height)
    x: adaptive.windowMargin
    y: adaptive.windowMargin
    minimumWidth: Math.min(adaptive.minimumWindowWidth, availableWindowWidth)
    minimumHeight: Math.min(adaptive.minimumWindowHeight, availableWindowHeight)
    width: Math.max(minimumWidth, availableWindowWidth - adaptive.windowMargin * 2)
    height: Math.max(minimumHeight, availableWindowHeight - adaptive.windowMargin * 2)
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


