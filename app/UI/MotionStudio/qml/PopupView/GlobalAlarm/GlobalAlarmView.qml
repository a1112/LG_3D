import QtQuick
import "../../Pages/AlarmPage/AlarmItem"
import "../Base"
PopupBase {
    id: root

    required property var adaptiveMetrics
    required property var style
    required property var modelStore
    required property var captureAlarmWatcher
    required property var apiClient
    required property var coreController
    required property var scriptLauncher

    width: root.adaptiveMetrics.boundedWidth(600, 440, 760)
    height: bodyV.height + root.adaptiveMetrics.headerSideGap
    Column{
        id:bodyV
        width: parent.width - root.adaptiveMetrics.mainSpacing
        anchors.centerIn:parent
        AlarmItemCameras{
            watcher: root.captureAlarmWatcher
            style: root.style
            apiClient: root.apiClient
            coreController: root.coreController
            width: parent.width
            alarmLevel: root.modelStore.coreGlobalError.errorLevelDict["相机"]
            height: root.adaptiveMetrics.scaleMetric(100, 82, 130)
        }
        AlarmItemNet{
            apiClient: root.apiClient
            modelStore: root.modelStore
            style: root.style
            scriptLauncher: root.scriptLauncher
            width: parent.width
            pollingEnabled: root.opened
            height: root.adaptiveMetrics.scaleMetric(100, 82, 130)
        }
        AlarmHardware {
            apiClient: root.apiClient
            style: root.style
            width: parent.width
            height: root.adaptiveMetrics.scaleMetric(100, 82, 130)
        }
    }
}
