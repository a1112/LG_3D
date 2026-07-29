import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../Comp/Card"
CardBase {
    id: root

    required property var coreController
    required property var popupManager
    required property var toolService
    required property var style
    required property var authManager

    cardStyle: root.style
    cardAuthManager: root.authManager

    readonly property var currentCoil: root.coreController.currentCoilModel

    Layout.fillWidth: true
    max_height:165//col.height+10
    title: root.currentCoil.coilNo
    // content_head_tool:ColorImageButton{
    //     source: "../icons/defectInfo.png"
    //     width: 30
    //     selectColor: Material.color(Material.LightGreen)
    //     height: 30
    //     ItemDelegate{
    //         anchors.fill: parent
    //         onClicked: {
    //             app.showDefectInfo()
    //         }
    //     }
    // }

    content_body:Item{
        id:col
        width:root.width
        Layout.fillWidth: true
        Layout.fillHeight: true
                visible: root.isShow
        Flow{
            anchors.fill: parent
            Layout.fillWidth: true
            Layout.fillHeight: true
            FlowRowItem{
                title:qsTr("流水号")
                value: root.currentCoil.coilId
                valueColor:Material.color(Material.Green)
            }
            FlowRowItem{
                title:qsTr("去向")
                value: root.currentCoil.nextInfo
            }
            FlowRowItem{
                title:qsTr("卷号 ")
                value: root.currentCoil.coilNo
            }
            FlowRowItem{
                title:qsTr("钢种 ")
                value: root.currentCoil.coilType
            }
            FlowRowItem{
                title:qsTr("外径 ")
                value: root.currentCoil.coilDia
            }
            FlowRowItem{
                title:qsTr("内径 ")
                value: root.currentCoil.coilInside
            }
            FlowRowItem{
                title:qsTr("卷宽 ")
                value: root.currentCoil.coilWidth
            }
            FlowRowItem{
                title:qsTr("卷厚 ")
                value: root.currentCoil.coilThickness
            }
            FlowRowItem{
                title:qsTr("日期 ")
                value: root.currentCoil.coilDetectionTime.dataString
            }
            FlowRowItem{
                title:qsTr("时间 ")
                value: root.currentCoil.coilDetectionTime.timeString
            }
        }
    }
    MouseArea{
        anchors.fill:parent
        acceptedButtons:Qt.RightButton
        onClicked:{
        menu.popup()
        }
    }
    Menu{
        id:menu
        MenuItem{
            text:qsTr("更多信息...")
            onClicked: root.popupManager.popupMsgPopView()
        }
    }


    LabelBase{
        font.bold:true
        font.pointSize:11
        anchors.right:parent.right
        anchors.top:parent.top
        text: root.toolService.getDelTimeStr(
                  root.coreController.nowTime,
                  root.currentCoil.coilCreateTime.dateTime)
    }

}
