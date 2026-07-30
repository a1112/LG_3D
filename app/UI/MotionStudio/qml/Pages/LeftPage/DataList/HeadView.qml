import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../btns"
import "../../Header"
Item {
    id: root

    required property var style
    required property var coreController
    required property var modelController
    required property var leftController
    required property var popupManager
    required property var apiClient
    required property bool showFilterIcon

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
        text: (root.modelController.currentCoilListIndex === 0
               ? qsTr("实时: ") : qsTr("历史: "))
              + root.modelController.currentCoilListModel.count
        font.pixelSize: 18
        font.bold:true
        color: root.modelController.currentCoilListTextColor
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
            text: root.coreController.currentCoilModel.coilNo
            font.pixelSize: 17
            font.family: "Arial"
            font.bold:true
            color: Material.color(Material.Blue)
            }
            Label{
            text: "     " + root.coreController.currentCoilModel.coilId
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
            style: root.style
            visible: root.modelController.isListHistoryModel
            id:its
            height: 26
            checked: false
            text:"退出"
            checkColor:Material.color(Material.Orange)
            fillWidth:true
            onClicked: {
             root.modelController.listToRealModel()
            }
        }

        FliterBtn{  // 筛选
            visible: root.showFilterIcon
            style: root.style
            leftController: root.leftController
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
            style: root.style
            tipText: qsTr("刷新")
            visible:true //! leftCore.searchViewShow
            anchors.fill: parent
            onClicked: {
                root.coreController.flushList()
            }
        }
        }
    }


ListToolMenu{
    id:listToolMenu
    modelController: root.modelController
    apiClient: root.apiClient
    popupManager: root.popupManager
// 脚本

}
}
