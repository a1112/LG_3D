import QtQuick
import QtQuick.Controls

MenuItem {
    property alias selectd:sw.checked
    onClicked:selectd=!selectd

    Switch{
        id:sw
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
    }
}
