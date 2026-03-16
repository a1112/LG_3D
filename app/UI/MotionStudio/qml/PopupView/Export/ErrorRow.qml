import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

RowLayout {
    id: root
    Layout.fillWidth: true
    property string errorStr: ""
    spacing: 10

    Label {
        text: "数据导出错误:"
        color: Material.color(Material.Red)
        font.bold: true
        Layout.alignment: Qt.AlignTop
    }

    TextArea {
        id: errorArea
        Layout.fillWidth: true
        Layout.preferredHeight: Math.max(80, implicitHeight)
        readOnly: true
        selectByMouse: true
        wrapMode: TextEdit.WrapAnywhere
        textFormat: TextEdit.PlainText
        text: root.errorStr
        color: Material.color(Material.Red)
        background: Rectangle {
            radius: 4
            border.width: 1
            border.color: Material.color(Material.Red)
            color: "transparent"
        }
    }

    Button {
        text: "复制"
        enabled: root.errorStr.length > 0
        Layout.alignment: Qt.AlignTop
        onClicked: {
            errorArea.selectAll()
            errorArea.copy()
            errorArea.deselect()
        }
    }
}
