import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Layouts

ItemDelegate {
    id: root
    required property string cameraKey
    required property int level
    required property string msg
    required property var style

    property string titleText: cameraKey
    property int alarmLevel: Number(level || 0)
    property string valueText: alarmLevel > 1 ? qsTr("异常") : qsTr("正常")
    property color valueColor: alarmLevel > 1
                                 ? style.statusErrorColor
                                 : style.statusSuccessColor

    ToolTip.visible: hovered
    ToolTip.text: msg || ""

    Frame {
        anchors.fill: parent
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        Label {
            text: root.titleText
            Layout.fillWidth: true
            elide: Text.ElideRight
        }

        Label {
            color: root.valueColor
            font.bold: true
            font.pixelSize: 18
            text: root.valueText
        }
    }
}
