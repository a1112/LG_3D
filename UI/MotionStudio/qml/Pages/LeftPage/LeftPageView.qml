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
        Material.background: Material.color(Material.BlueGrey)
        // height:ustb.height+5
    }

    SplitView {
        anchors.fill: parent
        spacing:8
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
            SplitView.fillWidth: true
            SplitView.preferredHeight: 25
        }

    }


}
