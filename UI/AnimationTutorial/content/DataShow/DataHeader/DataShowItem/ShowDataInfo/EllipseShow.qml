import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    Layout.fillHeight:true
    ColumnLayout{
        anchors.fill:parent
    EllipseDraw {
        Layout.fillHeight:true
        Layout.fillWidth:true
        ellipseWidth:0.9
        ellipseHeight:0.8
        ellipseRotation:45
    }
    TabBar{
        implicitHeight:40
        Layout.fillWidth:true
        TabButton{
            height:40
            text:"内径"
        }
        TabButton{
            height:40
            text:"外径"
        }
    }
}
}
