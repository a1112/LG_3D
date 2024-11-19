import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
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

        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }
        Label{
            text: "No:"
            color: "#747474"
        }
        Label{
            text: dataShowCore.currentCoilModel.coilNo
        }
        Label{
            text: "钢种:"
            color: "#747474"
        }
        Label{
            text: dataShowCore.currentCoilModel.coilType
        }

        Label{
            text: "外径:"
            color: "#747474"
        }
        Label{
            text: dataShowCore.currentCoilModel.coilDia
        }

        Label{
            text: "厚:"
            color: "#747474"
        }
        Label{
            text: dataShowCore.currentCoilModel.coilThickness
        }
        Label{
            text: "宽:"
            color: "#747474"
        }
        Label{
            text: core.currentCoilModel.coilWidth
        }
        Item{
            width: 30
            height: 1
        }

    }

}
