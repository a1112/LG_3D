import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../Base/IconButtons"
//  功能区域
Item {
    id:root
    width: 500
    height: 25

    Pane{
        anchors.fill: parent
        Material.elevation: 7
    }

    RowLayout{
        anchors.fill: parent
        Label{
            text:"" + defectCoreModel.currentListStartIndex

        }
        Label{
            text:" — " + defectCoreModel.currentListEndIndex

        }
        Label{
            text: "  NUM: "+defectCoreModel.defectsModel.count

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
