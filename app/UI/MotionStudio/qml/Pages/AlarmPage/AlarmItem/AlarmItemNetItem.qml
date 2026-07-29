import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ItemDelegate {
    id: root

    required property string titleText
    required property string valueText
    required property int level
    required property int port
    required property var style
    readonly property color valueColor: level > 1
                                           ? style.statusErrorColor
                                           : style.statusSuccessColor

    Frame {
        anchors.fill: parent
    }

    RowLayout {
        anchors.fill: parent

        Label {
            text: root.titleText
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
