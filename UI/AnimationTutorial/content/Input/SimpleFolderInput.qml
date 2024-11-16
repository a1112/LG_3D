import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
 import QtQuick.Dialogs
import "../Labels"
import "../Pages/Header"
RowLayout {
    id:root
    property alias value :value_id.text
    property alias placeholderText:value_id.placeholderText
    property string text: ""
        property string select_text: "选择..."
    Layout.fillWidth: true
    spacing:10
    FolderDialog{
        id:folderDialog
        onAccepted:{
            value_id.text=selectedFolder.toString().substring(8)
        }
    }

    KeyLabel {
        text: root.text
    }
    TextFieldBase{
        id:value_id
        Layout.fillWidth:true
    }
    CheckRec{
        fillWidth: true
        text:root.select_text
        onClicked:{
            folderDialog.open()
        }
    }
}
