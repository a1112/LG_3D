import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Material
Item {
    id: root

    required property var controller
    required property var chartController
    required property var style

    width: row.width
    height: 25

    Pane{
        anchors.fill: parent
        Material.elevation: 5
        Material.background: hh.hovered ? root.style.buttonHoverColor
                                        : root.style.panelElevatedColor
    }
    Frame{
    anchors.fill: parent
        }
    HoverHandler{
        id:hh
    }
    RowLayout{
        anchors.fill:parent
   }

    Row{
        id:row
        spacing: 2
        ItemDelegate{
            text: root.controller.chartShowType === 1
                  ? qsTr("高低 ▼") : qsTr("网格 ▼")
            font.family: "Material Icons"
            height: 25
            onClicked:{
                menu_type.popup()
            }
            Rectangle{
                border.color: root.style.headerBorderColor
                border.width: 1
                color: parent.hovered ? root.style.buttonHoverColor
                                      : root.style.panelElevatedColor
                anchors.fill: parent
            }
        }

        ItemDelegate{
            height: 25
            text: qsTr("网格: %1 mm").arg(root.chartController.tickSizeZ.toFixed(1))
        }

        ItemDelegate{
            height: 25
            text: qsTr("偏移: %1 mm").arg(root.chartController.offsetZ.toFixed(1))
        }
        ItemDelegate{
            height: 25
            text: qsTr("重置")
            onClicked: {
                root.chartController.reset()
            }
        }
    }
    Menu{
        id:menu_type
        MenuItem{
            text: "网格类型"
            font.bold: root.controller.chartShowType === 0
            onClicked:{
                root.controller.chartShowType = 0
            }
        }
        MenuItem{
            text: "高低值"
            font.bold: root.controller.chartShowType === 1
            onClicked:{
                root.controller.chartShowType = 1
            }
        }


    }

        }

