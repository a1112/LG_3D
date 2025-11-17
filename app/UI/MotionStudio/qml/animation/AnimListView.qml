import QtQuick
import QtQuick.Controls


ListView {

    add: Transition {


             SequentialAnimation {
                      NumberAnimation { properties: "x"; from: 500; duration: 1000 }
                      ColorAnimation { duration: 1000 }
                  }
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
