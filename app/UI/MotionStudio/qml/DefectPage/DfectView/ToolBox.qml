import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../Base/IconButtons"
//  功能区域
Item {
    id:root

    required property var defectModel

    width: 500
    height: 25

    Pane{
        anchors.fill: parent
        Material.elevation: 7
    }

    RowLayout{
        anchors.fill: parent
        Label{
            text:"" + root.defectModel.currentListStartIndex

        }
        Label{
            text:" — " + root.defectModel.currentListEndIndex

        }
        Label{
            text: "  NUM: " + root.defectModel.defectsModel.count

        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        Item{
            height: root.height
            width: height
            FullScreen{
                height: root.height
                onClicked:{
                }
            }
        }
        Item {
            width: 10
            Layout.fillHeight: true
        }

    }
}
