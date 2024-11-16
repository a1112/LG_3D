import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
Item {

    Pane{
        anchors.centerIn: parent
        width: parent.width-14
        height: parent.height-14
        Material.elevation: 11

        Label{
            text: "无报警"
            anchors.centerIn: parent
            font.pixelSize: 26

        }

    }

}
