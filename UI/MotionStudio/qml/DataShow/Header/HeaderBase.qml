import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
Item {
    Pane{
        id: pane
        anchors.fill: parent
        Material.elevation:6
    }
    MouseArea{
        anchors.fill:parent
        acceptedButtons:Qt.RightButton
        onClicked:{
            titleMenu.popup()
        }
    }
    MouseArea{
        anchors.fill: parent
        acceptedButtons:Qt.LeftButton
        onDoubleClicked: {
            surfaceData.showMax = !surfaceData.showMax
        }
    }
}
