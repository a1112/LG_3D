import "../Labels"
import "../Pages/Header"
import QtQuick.Layouts
import QtQuick.Dialogs

RowLayout {
    id:root
    property alias value :value_id.text
    property string text: ""
    property string select_text: "选择..."
    property alias currentFolder:dialog.currentFolder
    property alias acceptLabel:dialog.acceptLabel
    property alias placeholderText: value_id.placeholderText
    property alias nameFilters:dialog.nameFilters
    Layout.fillWidth: true
    spacing:10
    FileDialog{
        id:dialog
        fileMode : FileDialog.SaveFile
        onAccepted:{
            if (fileMode == FileDialog.SaveFile) {
                let s_text =tool.url_to_str(selectedFile)
                if (!s_text.toLowerCase().endsWith(selectedNameFilter.name.toLowerCase())) {
                        value_id.text= s_text + selectedNameFilter.name
                    }
                else {
                    value_id.text = s_text

                }
            }
            else{
            value_id.text=tool.url_to_str(selectedFile)
            }
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
            dialog.open()
        }
    }
}
