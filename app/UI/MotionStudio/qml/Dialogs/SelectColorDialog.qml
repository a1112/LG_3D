import Qt.labs.platform
ColorDialog {
    id: root

    property var acceptFunc
    onAccepted:{
        let callback = root.acceptFunc
        if (typeof callback === "function") {
            callback(root.color)
        }
    }
}
