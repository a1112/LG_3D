import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
Label {
    id: root
    Layout.fillWidth: true

    background: Rectangle {
        color: root.palette.alternateBase
        border.color: root.palette.mid
        border.width: 1
        radius: 3
    }

}
