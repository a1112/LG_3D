import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
RowLayout {

    property string title
    property alias text:tf.text


    Label {
        text: title+" : "

    }
    TextField {
        id:tf
        Layout.fillWidth: true

    }
}
