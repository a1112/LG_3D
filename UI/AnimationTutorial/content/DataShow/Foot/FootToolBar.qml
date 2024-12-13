import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

import "../ViewChang"

Item {
    id:root
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
                height: root.height
                text: "视图"
                selected: dataShowCore.viewRendererListView
                onClicked: {
                    dataShowCore.viewRendererListView =! dataShowCore.viewRendererListView
                }
            }
            ItemDelegateItem {
                height: root.height
                text: "高低值"
                selected: dataShowCore.viewRendererMaxMinValue
                onClicked: {
                    dataShowCore.viewRendererMaxMinValue =! dataShowCore.viewRendererMaxMinValue
                }
            }
            Rectangle{
                width: 1
                height: root.height-6
                anchors.verticalCenter: parent.verticalCenter
                color: "#0090E0"
            }
        }
        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }
        // CoilInfoRow{}
        ToolBoxViewRow{

        }
        Item{
            width: 30
            height: 1
        }

    }

}
