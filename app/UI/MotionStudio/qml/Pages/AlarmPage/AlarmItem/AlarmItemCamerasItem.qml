import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ItemDelegate {
    id: root
    property string titleText: Key
    property int alarmLevel: Number(level || 0)
    property string valueText: alarmLevel > 1 ? qsTr("异常") : qsTr("正常")
    property string valueColor: alarmLevel > 1 ? Material.color(Material.Red) : Material.color(Material.Green)

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
