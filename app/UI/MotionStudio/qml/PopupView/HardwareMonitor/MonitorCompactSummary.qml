import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root

    required property var style
    property string label: ""
    property string value: ""
    property bool healthy: false

    spacing: 5

    MonitorStatusDot {
        style: root.style
        active: root.healthy
    }

    Label {
        text: root.label
        color: root.style.labelColor
    }

    Label {
        text: root.value
        color: root.healthy
               ? root.style.statusSuccessColor
               : root.style.statusWarningColor
        font.bold: true
    }
}
