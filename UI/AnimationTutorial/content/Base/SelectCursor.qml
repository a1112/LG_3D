import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../Labels"
Item{
    id:root
    width: selectItem.width
    height: selectItem.height
    x:selectItem.x
    y:selectItem.y
    opacity: 0.9
    Behavior on x{
        NumberAnimation{duration: 300}
    }
    Behavior on y{
        NumberAnimation{duration: 300}
    }
    Behavior on width{
        NumberAnimation{duration: 300}
    }
    Behavior on height{
        NumberAnimation{duration: 300}
    }
    property int maxLen: Math.max(width,height)
    Item {     // 指针
        anchors.centerIn: parent
        width: maxLen*2
        height: maxLen*2
//        scale: 2.5
        Rectangle{
            color: "red"
            radius: width
            anchors.centerIn: parent
            width: 3
            height: width
            opacity: 0.7
        }
        Rectangle{
            color: "red"
            width: 3
            height: 5
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Rectangle{
            color: "red"
            width: 3
            height: 5
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Rectangle{
            color: "red"
            width: 5
            height: 3
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
        }
        Rectangle{
            color: "red"
            width: 5
            height: 3
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
        }
    }
Column {
    anchors.right: root.left
    anchors.bottom: root.top
    LabelTitle{
        text: control.getNameById(selectDefectObj.defectID)
        color:"red"
    }
}
}
