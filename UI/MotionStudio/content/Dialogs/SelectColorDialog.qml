import Qt.labs.platform
ColorDialog {
    property var acceptFunc
    onAccepted:{
        acceptFunc(color)
    }
}
