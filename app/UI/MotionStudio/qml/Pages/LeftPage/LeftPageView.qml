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
    Pane{
        width: parent.width
        Material.elevation: 5
        Material.background: coreStyle.panelBackgroundColor
        // height:ustb.height+5
    }
    Rectangle {
        anchors.fill: parent
        color: coreStyle.panelBackgroundColor
    }

    SplitView {
        anchors.fill: parent
        spacing: adaptive.mainSpacing
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
        }

        SearchView{ // 查询界面
            visible: leftCore.searchViewShow
            Layout.fillWidth: true
            SplitView.fillWidth: true
        }

        FliterSelectView{ // 过滤界面
        }

        DataListView{   // 左侧列表
            id:dataList
        }

        FootView{
            apiClient: api
            style: coreStyle
            model: coreModel
            popupManager: popManage
            SplitView.fillWidth: true
            SplitView.preferredHeight: adaptive.scaleMetric(25, 22, 34)
        }

    }


}
