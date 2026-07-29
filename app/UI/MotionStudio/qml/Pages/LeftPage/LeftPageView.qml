import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
import "../../Pages/Card"
import "../../Pages/AlarmPage"
import "../../Pages/AlarmPage/AlarmItemSimple"
import "../../Pages/AlarmPage/AlarmCheckInfo"
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
        }
        // AlarmInfoGlob{// 全局报警信息
        //     SplitView.fillWidth: true
        //     Layout.fillWidth: true
        // }
        AlarmCheckInfoView{  // 判级
            width: parent.width
        }
        AlarmItemSimple{    // 报警
            width: parent.width
            alarmInfo: root.alarmInfo
            apiClient: root.apiClient
        }

        SearchView{ // 查询界面
            visible: root.leftController.searchViewShow
            adaptiveMetrics: root.adaptiveMetrics
            style: root.style
            leftController: root.leftController
            Layout.fillWidth: true
            SplitView.fillWidth: true
        }

        FliterSelectView{ // 过滤界面
        }

        DataListView{   // 左侧列表
            id:dataList
            style: root.style
            coreController: root.coreController
            modelController: root.modelStore
            leftController: root.leftController
            popupManager: root.popupManager
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
