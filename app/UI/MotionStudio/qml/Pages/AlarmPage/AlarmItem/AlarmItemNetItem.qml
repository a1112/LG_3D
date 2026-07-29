import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ItemDelegate {
    id: root

    property string title: "数据"
    property string valueText: ""
    property int level: 0
    readonly property color valueColor: level > 1
                                           ? Material.color(Material.Red)
                                           : Material.color(Material.Green)

    Frame {
        anchors.fill: parent
    }

    RowLayout {
        anchors.fill: parent

        Label {
            text: root.title
        }

        Label {
            text: ":"
        }

        Label {
            color: root.valueColor
            font.bold: true
            font.pixelSize: 20
            text: root.valueText
        }
    }
}
