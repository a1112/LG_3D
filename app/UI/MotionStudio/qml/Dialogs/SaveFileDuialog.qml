import QtQuick.Dialogs

FileDialog {
    fileMode : FileDialog.SaveFile

    property var acceptFunc

    onAccepted: {
        let select_file = tool.url_to_str(selectedFile)
        return acceptFunc(select_file)
    }

}
