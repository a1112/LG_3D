import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../btns"
Item {
    Layout.fillWidth: true
    height: 25
    Pane {
        anchors.fill: parent
        Material.elevation: 3
    }

    RowLayout{
    anchors.fill: parent

    Row{
        Layout.alignment: Qt.AlignVCenter
        spacing: 5
        Repeater{
            model:coreModel.toolBarModel
            delegate:ToolBtn{
                height: 25
                width: 25
                source: source_icon
            }
        }
    }


    }


}
