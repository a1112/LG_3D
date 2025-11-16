import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../../Labels"
// import "../../../btns"
RowLayout {

    property alias title: title_id.text
    property real value
    height: 30
    width:parent.width
    Layout.fillWidth: true
    KeyLabel {
        id:title_id
        text: "内径测量"
        opacity: 0.8
        font.bold: true
    }
    ValueTextLabel{
        Layout.fillWidth: true
        id:value_id
        text: value.toFixed(2)
    }
    KeyLabel {
        text: "mm"
        opacity: 0.8
        font.bold: true
    }

    Item{
        width: 10
        height: 1
    }
}
