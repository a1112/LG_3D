import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
Item {
    id: root
    signal maximizeRequested()

    Pane{
        id: pane
        anchors.fill: parent
        Material.elevation:6
    }
    MouseArea{
        anchors.fill: parent
        acceptedButtons:Qt.LeftButton
        onDoubleClicked: {
            root.maximizeRequested()
        }
    }
}
