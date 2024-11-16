import QtQuick
import QtQuick.Controls


ListView {

    add: Transition {
             NumberAnimation { properties: "x"; from: 300; duration: 500 }
         }
}
