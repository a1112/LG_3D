import QtQuick 2.15
import QtQuick.Controls.Material
import "../Base"
import "../Core"

Item {
    id:item
    property alias text: itemDelegate.text
    property bool checked: true
    width: itemDelegate.width
    property var checkColor: Material.color(Material.Blue)
    property int typeIndex: 0
    property bool fillWidth: false
    property int fillWidthWidth: 1
    signal clicked
    height: root.height-12

    Pane{
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        Material.elevation: 12

    }
    Rectangle{
        anchors.horizontalCenter: parent.horizontalCenter
        width: typeIndex?4:parent.width
        height: 2
        anchors.top: parent.top
        color: checkColor
        visible: item.checked && !fillWidth
    }
    Rectangle{
        anchors.horizontalCenter: parent.horizontalCenter
        width:  typeIndex?parent.width:4
        height: 2
        anchors.bottom: parent.bottom
        color: checkColor
        visible: item.checked && !fillWidth
    }

    Rectangle{
        visible: fillWidth
        anchors.fill: parent
        color:"transparent"
        border.color: checkColor
        border.width: fillWidthWidth
    }
ItemDelegate{
    height: parent.height
    font.bold: true
    font.pixelSize: 15
    id:itemDelegate

    onClicked: {
    item.checked = !item.checked
        item.clicked()
    }
}



}
