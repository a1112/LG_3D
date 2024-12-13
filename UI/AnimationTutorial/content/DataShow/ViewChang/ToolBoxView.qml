import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id:root
    Frame{
    anchors.fill: parent
    }
    RowLayout{
        anchors.fill:parent
        Item{
            Layout.fillWidth:true
            Layout.fillHeight:true
        }
        ColumnLayout{
            Layout.fillHeight:true
            CheckDelegate{
                text:"3D 切换"
                implicitHeight:root.height/2
                height: implicitHeight
            }
            CheckDelegate{
                text:"2D 切换"
                implicitHeight:root.height/2
                height: implicitHeight
            }
        }
    }

}
