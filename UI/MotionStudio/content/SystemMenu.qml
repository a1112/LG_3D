import QtQuick
import QtQuick.Controls.Material

MenuBar {
    id: menuBar
    contentHeight: 10
    height: 10
    background:Rectangle {
        color: "transparent"
    }
    Menu {
            height: 10
        id: fileMenu
        title: qsTr("File")
        // ...
    }

}
