import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../Rectange"

MenuItem {
    id: root

    property color selectedColor

    text: qsTr("前景色")

    onTriggered: {
        colorDialog.selectedColor = root.selectedColor
        colorDialog.open()
    }

    ColorDialog {
        id: colorDialog
        onAccepted: root.selectedColor = selectedColor
    }

    ColorRec {
        anchors.right: parent.right
        height: parent.height
        recColor: root.selectedColor
    }
}
