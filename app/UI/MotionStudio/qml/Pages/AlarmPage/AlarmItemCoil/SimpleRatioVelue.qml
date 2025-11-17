import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../../Labels"
import "../../../btns"
RowLayout {

    property alias title: title_id.text
    property real value_1:0.0
    property real value_2:0.0
    height: 30
    spacing: 5
    width:parent.width
    Layout.fillWidth: true
    KeyLabel {
        id:title_id
        text: ""
        opacity: 0.8
        font.bold: true
    }
    HovValueTextLabel{
        Layout.fillWidth: true
        id:value_id
        text: value_1.toFixed(0)
    }
    KeyLabel {
        text: "长边"
        opacity: 0.8
        font.bold: true
    }
    HovValueTextLabel{
        Layout.fillWidth: true
        id:value_id2
        text: value_2.toFixed(0)
    }
    HovValueTextLabel{
        Layout.fillWidth: true
        show_level:Math.abs(value_2)>70?3:value_2>30?2:1
        toolTipText:"拟合长边/短边"
        text: (value_2/value_1).toFixed(2)
    }

    Item{
        width: 10
        height: 1
    }
}
