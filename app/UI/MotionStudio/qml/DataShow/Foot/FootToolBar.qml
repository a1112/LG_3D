import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

import "../ViewChang"

Item {
    id: root
    required property var surfaceData
    required property var controller
    required property var style
    height: 25
    width: parent.width
    Pane{
        anchors.fill: parent
        Material.elevation: 8
    }
    RowLayout{
        anchors.fill: parent
        Row{
            ItemDelegateItem {
                style: root.style
                height: root.height
                text: qsTr("视图")
                selected: root.controller.viewRendererListView
                onClicked: {
                    root.controller.viewRendererListView = !root.controller.viewRendererListView
                }
            }
            ItemDelegateItem {
                style: root.style
                height: root.height
                text: qsTr("高低值")
                selected: root.controller.viewRendererMaxMinValue
                onClicked: {
                    root.controller.viewRendererMaxMinValue = !root.controller.viewRendererMaxMinValue
                }
            }

            Rectangle{
                width: 1
                height: root.height-6
                anchors.verticalCenter: parent.verticalCenter
                color: root.style.headerBorderColor
            }
        }

        FootMsg {
            surfaceData: root.surfaceData
            style: root.style
        }

        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }
        // CoilInfoRow{}
        ToolBoxViewRow {
            surfaceData: root.surfaceData
            controller: root.controller
        }
        Item{
            width: 30
            height: 1
        }

    }

}
