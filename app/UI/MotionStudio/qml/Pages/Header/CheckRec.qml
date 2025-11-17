import QtQuick
import QtQuick.Controls.Material


Item {
    id:item
    property alias font: cetLabel.font
    property alias text: cetLabel.text
    property bool checked: true
    width: cetLabel.width + 25
    property color checkColor: Material.color(Material.Blue)
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
    }


    Rectangle{
        anchors.horizontalCenter: parent.horizontalCenter
        width: item.typeIndex?4:parent.width
        height: 2
        anchors.top: parent.top
        color: item.checkColor
        visible: item.checked && ! item.fillWidth

    }
    Rectangle{
        anchors.horizontalCenter: parent.horizontalCenter
        width:  item.typeIndex?parent.width:4
        height: 2
        anchors.bottom: parent.bottom
        color: item.checkColor

        visible: item.checked && !item.fillWidth
    }

    Rectangle{
        visible: item.fillWidth
        anchors.fill: parent
        color:"transparent"
        border.color: item.checkColor
        border.width: item.fillWidthWidth

    }
    ItemDelegate{
        height: parent.height
        font.bold: true
        font.pixelSize: 15
        id:itemDelegate
        anchors.fill:parent
        onClicked: {
            item.checked = !item.checked
            item.clicked()
        }
    }

    Label{
        id:cetLabel
        font.bold: true
        font.pointSize: 14
        anchors.centerIn:parent
    }

}
