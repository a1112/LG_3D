import QtQuick
import QtQuick.Controls


ListView {

    add: Transition {
             NumberAnimation { properties: "x"; from: 300; duration: 500 }
         }

    spacing:5
    highlight: Rectangle {
        color: "lightsteelblue"
        radius: 5
        border.color: "steelblue"
        border.width: 3
    }
    ScrollBar.vertical: ScrollBar {
    }
}
