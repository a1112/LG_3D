import QtQuick
import QtQuick.Controls.Material


Item {
    id: root

    required property var style

    property alias font: cetLabel.font
    property alias text: cetLabel.text
    property bool checked: true
    width: cetLabel.width + 25
    property color checkColor: root.style.accentColor
    property alias color:cetLabel.color
    property int typeIndex: 0
    property bool fillWidth: false
    property int fillWidthWidth: 1
    signal clicked
    // height: root.height-12
    height:30
    Pane{
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        Material.elevation: 4
        Material.background: root.style.headerBackgroundColor
    }


    Rectangle{
        anchors.horizontalCenter: parent.horizontalCenter
        width: root.typeIndex ? 4 : parent.width
        height: 2
        anchors.top: parent.top
        color: root.checkColor
        visible: root.checked && !root.fillWidth

    }
    Rectangle{
        anchors.horizontalCenter: parent.horizontalCenter
        width: root.typeIndex ? parent.width : 4
        height: 2
        anchors.bottom: parent.bottom
        color: root.checkColor

        visible: root.checked && !root.fillWidth
    }

    Rectangle{
        visible: root.fillWidth
        anchors.fill: parent
        color: root.style.headerBackgroundColor
        border.color: root.checkColor
        border.width: root.fillWidthWidth

    }
    ItemDelegate{
        height: parent.height
        font.bold: true
        id:itemDelegate
        anchors.fill:parent
        background: Rectangle {
            color: itemDelegate.hovered ? root.style.buttonHoverColor : root.style.headerBackgroundColor
        }
        onClicked: {
            root.checked = !root.checked
            root.clicked()
        }
    }

    Label{
        id:cetLabel
        font.bold: true
        anchors.centerIn:parent
    }

}
