import QtQuick 2.14
import QtQuick.Controls 2.14
import QtQuick.Controls.Material 2.14
Item{
    id:root
    property color border_color : Material.color(Material.Indigo)
    property real border_width: 2
    property bool borderCanview: true
    property bool checked: false
    Rectangle{
        id:top
        color:  border_color
        visible: borderCanview
        height: border_width
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.checked?parent.width:0
        Behavior on width{NumberAnimation{duration: 400}}
    }

    Rectangle{
        color: border_color
        height: border_width
        visible: borderCanview
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom:  parent.bottom
        width: root.checked?parent.width:0
        Behavior on width{NumberAnimation{duration: 400}}
    }
    Rectangle{
        color: border_color
        width:  border_width
        visible: borderCanview
        anchors.verticalCenter:  parent.verticalCenter
        anchors.left:   parent.left
        height: root.checked?parent.height:0
        Behavior on height{NumberAnimation{duration: 400}}
    }
    Rectangle{
        color: border_color
        width:  border_width
        visible: borderCanview
        anchors.verticalCenter:  parent.verticalCenter
        anchors.right:   parent.right
        height: root.checked?parent.height:0
        Behavior on height{NumberAnimation{duration: 400}}
    }
}


