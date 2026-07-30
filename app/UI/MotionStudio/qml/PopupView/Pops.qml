import QtQuick
import "Export"
import "Connect"
import "DefectClass"
import "ToolsMenu"
import "ApiListPop"
import "MsgPop"
import "Backup"
import "ReDetection"
import "GlobalAlarm"
import "HardwareMonitor"
import "../SettingPage"
import "../Style"
import "HelpPop"
import "AlgTest"
import "ClipSetting"
import "../Pages/LeftPage/DataList/DataListMenu"
Item {
    id: root

    required property var apiClient
    required property var adaptiveMetrics
    required property var appStyle
    required property var settingsStore
    required property var appInfo
    required property var downloadClient
    required property var authManager
    required property var graphsManager
    required property var deviceCurveManager
    required property var modelStore
    required property var clipboardService
    required property var toolService
    required property var globalContext
    required property var dialogManager
    required property var captureAlarmWatcher
    required property var coreController
    required property var scriptLauncher

    ConnectDialog {
        id: connectDialog
        adaptiveMetrics: root.adaptiveMetrics
        settings: root.settingsStore
        style: root.appStyle
    }//连接 菜單
    function popupConnectDialog(){connectDialog.open()}
    ExportView{
        id: exportView
        adaptiveMetrics: root.adaptiveMetrics
        style: root.appStyle
        modelStore: root.modelStore
        toolService: root.toolService
        apiClient: root.apiClient
        downloadClient: root.downloadClient
    }   //导出菜单
    function popupExportView(){exportView.openDialog()}
    ToolsMenuView{
        id: toolsMenu
        apiClient: root.apiClient
        scriptLauncher: root.scriptLauncher
        popupManager: root
        dialogManager: root.dialogManager
    } // 右侧功能菜单
    function popupToolsMenuView(){toolsMenu.popup()}
    DefectClassPop{
        id:defectClassPop
        adaptiveMetrics: root.adaptiveMetrics
        globalContext: root.globalContext
        apiClient: root.apiClient
        dialogManager: root.dialogManager
    }// 缺陷列表
    function popupDefectClassPop(){defectClassPop.popup()}
    ApiListPopView {
        id: apiListPop
        adaptiveMetrics: root.adaptiveMetrics
        apiClient: root.apiClient
        style: root.appStyle
    } // API 调用记录表
    function popupApiList(){apiListPop.popup()}
    MsgPopView {
        id: msg_popup
        adaptiveMetrics: root.adaptiveMetrics
        coreController: root.coreController
        modelStore: root.modelStore
        apiClient: root.apiClient
        style: root.appStyle
    }    // 詳細信息
    function popupMsgPopView(){msg_popup.popup()}
      SettingPageView{
          id:coreSetting_view
          apiClient: root.apiClient
          style: root.appStyle
          settings: root.settingsStore
          coreController: root.coreController
          appInfo: root.appInfo
        downloadClient: root.downloadClient
    }    // 设置界面
    function openSettingPageView(){coreSetting_view.open()}
    StyleMenu{
        id:menuStyle
        style: root.appStyle
        settings: root.settingsStore
        popupManager: root
        authManager: root.authManager
        graphsManager: root.graphsManager
        deviceCurveManager: root.deviceCurveManager
    } // 主题菜单
    function popupStyleMenu(){menuStyle.popup()}
    ClipSettingView{
        id:clipSettingView
        apiClient: root.apiClient
        settings: root.settingsStore
        style: root.appStyle
    }
    function popupClipSettingView(){clipSettingView.openDialog()}
    BackupDataView{
        id: backupDataView
        adaptiveMetrics: root.adaptiveMetrics
        modelStore: root.modelStore
        apiClient: root.apiClient
        style: root.appStyle
        toolService: root.toolService
    }   // 数据备份
    function popupBackupDataView(){backupDataView.popup()}
    ReDetectionView{
        id: reDetectonView
        modelStore: root.modelStore
        apiClient: root.apiClient
        style: root.appStyle
    }  //重新识别
    function popupReDetectionView(fromId, toId){
        if (fromId !== undefined && toId !== undefined){
            reDetectonView.setRange(fromId, toId)
        }else{
            reDetectonView.useAutoRange = true
        }
        reDetectonView.popup()
    }
    GlobalAlarmView{
        id: globalAlarmView
        adaptiveMetrics: root.adaptiveMetrics
        style: root.appStyle
        modelStore: root.modelStore
        captureAlarmWatcher: root.captureAlarmWatcher
        apiClient: root.apiClient
        coreController: root.coreController
        scriptLauncher: root.scriptLauncher
    } // 设备报警
    function popupGlobalAlarmView(){globalAlarmView.popup()}
    HardwareMonitorView{
        id:hardwareMonitorView
        apiClient: root.apiClient
        adaptiveMetrics: root.adaptiveMetrics
        style: root.appStyle
    }
    function popupHardwareMonitorView(){hardwareMonitorView.popup()}
    DataListItemMenu{
        id:lefeListMemu
        apiClient: root.apiClient
        modelStore: root.modelStore
        clipboardService: root.clipboardService
        toolService: root.toolService
        popupManager: root
    } // 左侧列表
    function popupDataListItemMenu(coilModel){
        lefeListMemu.coilModel = coilModel
        lefeListMemu.popup()}
    HelpPopView{
        id: helpMenu
        adaptiveMetrics: root.adaptiveMetrics
        appInfo: root.appInfo
        style: root.appStyle
    }
    function popupHelpView(){helpMenu.popup()}
    AlgTestDialog{
        id:algTestDialog
        apiClient: root.apiClient
        adaptiveMetrics: root.adaptiveMetrics
        style: root.appStyle
    }
    function popupAlgTestDialog(){algTestDialog.openDialog()}
}
