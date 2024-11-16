import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../Base/IconButtons"
//  功能区域
Item {
    id:root
    width: 500
    height: 25

    Pane{
        anchors.fill: parent
    }

    RowLayout{
        anchors.fill: parent
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
        Item{
            height: root.height
            width: height
            FullScreen{
                height: root.height
                onClicked:{



                }

            }
        }
        Item {
            width: 10
            Layout.fillHeight: true
        }

    }
}
