import QtQuick
import QtQuick.Controls
Row {
    property alias title: label.text
    property alias value: tf.text
    Label{
        id:label
        text: qsTr("起始:")
        font.bold: true
        anchors.verticalCenter: parent.verticalCenter
    }
    TextField{
        id:tf
        width: 160
        selectByMouse: true
        implicitHeight: 40
        anchors.verticalCenter: parent.verticalCenter
    }

}
