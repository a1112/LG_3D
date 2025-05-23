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


Item {
    id:root
    Pane{
        anchors.fill: parent
        Material.elevation: 5
        // Material.background:"#201F28"
    }
    Pane{
        width: parent.width
        Material.elevation: 5
        Material.background: Material.color(Material.BlueGrey)
        // height:ustb.height+5
    }

    SplitView {
        anchors.fill: parent
        spacing:8
        orientation: Qt.Vertical
        CurrentInfo{ // 当前卷信息
            SplitView.fillWidth: true
        }
        // AlarmInfoGlob{// 全局报警信息
        //     SplitView.fillWidth: true
        //     Layout.fillWidth: true
        // }
        AlarmCheckInfoView{

            visible: true
            width: parent.width
        }
        AlarmItemSimple{
            visible:true
            width: parent.width
        }

        SearchView{ // 查询界面
            visible: leftCore.searchViewShow
            Layout.fillWidth: true
            SplitView.fillWidth: true
        }

        FliterSelectView{

        }

        DataListView{   // 左侧列表
            SplitView.fillWidth: true
            SplitView.fillHeight: true
            id:dataList
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        FootView{
            SplitView.fillWidth: true
            SplitView.preferredHeight: 25
        }

    }


}
