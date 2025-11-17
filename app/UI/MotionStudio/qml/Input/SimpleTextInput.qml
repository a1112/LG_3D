import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Labels"
RowLayout {
    id:root
    property alias value:field.text
    property string text: ""
    Layout.fillWidth: true
    spacing:10
    KeyLabel {
        text: root.text
    }
    TextFieldBase{
        id:field
        Layout.fillWidth:true
    }

}
