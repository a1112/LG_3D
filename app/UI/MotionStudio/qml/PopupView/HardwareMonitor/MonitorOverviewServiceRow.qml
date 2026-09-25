pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    required property var style
    required property var model
    required property int index

    color: index % 2 ? style.panelAlternateColor : "transparent"
    radius: 3

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 7
        anchors.rightMargin: 7

        MonitorStatusDot {
            style: root.style
            active: root.model.online
        }

        Label {
            text: root.model.serviceName
            color: root.style.titleColor
            font.bold: true
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        Label {
            text: root.model.hasPort ? ":" + root.model.port : ""
            color: root.style.secondaryTextColor
        }

        Label {
            text: root.model.online ? "运行中" : "未运行"
            color: root.model.online
                   ? root.style.statusSuccessColor : root.style.statusErrorColor
        }
    }
}
