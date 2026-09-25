import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
import "../../Pages/Card"
import "../../Pages/AlarmPage"
import "../../Pages/AlarmPage/AlarmItemSimple"
import "DataList"
import "SearchView"
import "FliterSelect"

/*
    左侧列表
*/
Item {
    id:root

    required property var adaptiveMetrics
    required property var style
    required property var modelStore
    required property var popupManager
    required property var leftController
    required property var apiClient
    required property var alarmInfo
    required property var coreController
    required property var toolService
    required property var authManager
    required property var globalContext

    Pane{
        width: parent.width
        Material.elevation: 5
        Material.background: root.style.panelBackgroundColor
        // height:ustb.height+5
    }
    Rectangle {
        anchors.fill: parent
        color: root.style.panelBackgroundColor
    }

    SplitView {
        anchors.fill: parent
        spacing: root.adaptiveMetrics.mainSpacing
        orientation: Qt.Vertical
        CurrentInfo{ // 卷信息
            SplitView.fillWidth: true
            coreController: root.coreController
            popupManager: root.popupManager
            toolService: root.toolService
            style: root.style
            authManager: root.authManager
        }
        // AlarmInfoGlob{// 全局报警信息
        //     SplitView.fillWidth: true
        //     Layout.fillWidth: true
        // }
        AlarmItemSimple{    // 报警
            width: parent.width
            alarmInfo: root.alarmInfo
            apiClient: root.apiClient
            style: root.style
            authManager: root.authManager
        }

        SearchView{ // 查询界面
            visible: root.leftController.searchViewShow
            adaptiveMetrics: root.adaptiveMetrics
            style: root.style
            leftController: root.leftController
            authManager: root.authManager
            modelStore: root.modelStore
            Layout.fillWidth: true
            SplitView.fillWidth: true
        }

        FliterSelectView{ // 过滤界面
            leftController: root.leftController
            globalContext: root.globalContext
            style: root.style
        }

        DataListView{   // 左侧列表
            id:dataList
            style: root.style
            coreController: root.coreController
            modelController: root.modelStore
            leftController: root.leftController
            popupManager: root.popupManager
            apiClient: root.apiClient
            globalContext: root.globalContext
        }

        FootView{
            apiClient: root.apiClient
            style: root.style
            model: root.modelStore
            popupManager: root.popupManager
            SplitView.fillWidth: true
            SplitView.preferredHeight: root.adaptiveMetrics.scaleMetric(25, 22, 34)
        }

    }


}
