import QtQuick.Dialogs

FileDialog {
    id: root

    required property var toolService

    fileMode : FileDialog.SaveFile

    property var acceptFunc

    onAccepted: {
        let selectedPath = root.toolService.url_to_str(root.selectedFile)
        let callback = root.acceptFunc
        if (typeof callback === "function") {
            callback(selectedPath)
        }
    }

}
