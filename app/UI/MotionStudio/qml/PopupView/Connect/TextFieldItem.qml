import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
RowLayout {
    id: root

    property string title
    property alias text:tf.text
    function forceInputFocus() {
        tf.forceActiveFocus()
        tf.selectAll()
    }


    Label {
        text: root.title + "："

    }
    TextField {
        id:tf
        Layout.fillWidth: true

    }
}
