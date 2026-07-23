import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
Item{
    id:root
    width: parent.width
    height: 40
    property alias text :tf.text
    property alias title: titleId.text
    property alias placeholderText: tf.placeholderText
    Row{
        anchors.fill: parent
        spacing: 0
        Label{
            anchors.verticalCenter: parent.verticalCenter
            id:titleId
            text: "名称"
            font.bold: true
            font.pixelSize: 15
            width: 85
        }
        TextField{
            id:tf
            selectByMouse: true
            width: root.width-titleId.width
            height: parent.height
            Layout.fillWidth: true
            placeholderText: "--------"
        }
    }
}
