import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../btns"
import "../../Header"
Item {
    Layout.fillWidth: true
    height: 30
    Pane {
        id: pane
        anchors.fill: parent
        Material.elevation: 6
    }
    MouseArea{
        acceptedButtons: Qt.RightButton
        anchors.fill: parent
        onClicked:{
        listToolMenu.popup()

        }
    }
    RowLayout{
        anchors.fill: parent
        spacing: 5
        Label{
        text:(coreModel.currentCoilListIndex==0? "实时: " :"历史: ")+coreModel.currentCoilListModel.count
        font.pixelSize: 18
        font.bold:true
        color: coreModel.currentCoilListTextColor
        Layout.alignment: Qt.AlignVCenter

        }

        Row{
            visible: true
            Label{
            text:"  "
            font.pixelSize: 13
            anchors.verticalCenter: parent.verticalCenter
            }
            Label{
            text:core.currentCoilModel.coilNo
            font.pixelSize: 17
            font.family: "Arial"
            font.bold:true
            color: Material.color(Material.Blue)
            }
            Label{
            text: "     " +core.currentCoilModel.coilId
            font.pixelSize: 15

            anchors.verticalCenter: parent.verticalCenter
            }

        }
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        CheckRec{
            visible:coreModel.isListHistoryModel
            id:its
            height: 26
            checked: false
            text:"退出"
            checkColor:Material.color(Material.Orange)
            fillWidth:true
            onClicked: {
             coreModel.listToRealModel()
            }
        }

        FliterBtn{  // 筛选

        }

        // Item{
        //        height: parent.height
        //        width: height
        // ExportButton{
        //     tipText: "导出"
        //     visible:auth.isAdmin
        //     anchors.fill: parent
        //     onClicked: {
        //        popManage.popupExportView()
        //     }
        // }
        // }
        Item{
               height: parent.height
               width: height
        FlushButton{
            tipText: "刷新"
            visible:true //! leftCore.searchViewShow
            anchors.fill: parent
            onClicked: {
                core.flushList()
            }
        }
        }
    }


ListToolMenu{
    id:listToolMenu
// 脚本

}
}
