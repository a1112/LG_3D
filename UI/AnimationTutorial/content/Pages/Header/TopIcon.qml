import QtQuick
import "../../Base" as Base
Item{
    height:root.height+5
    width:ustb.width
    Base.USTB{
        id:ustb
        height:parent.height
        MouseArea{
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onClicked: {
                coreStyle.isDark=!coreStyle.isDark
            }
        }
        MouseArea{
            anchors.fill: parent
            acceptedButtons: Qt.RightButton
            onClicked: {
                coreStyle.openStyleDialog()
            }
        }
    }
}
