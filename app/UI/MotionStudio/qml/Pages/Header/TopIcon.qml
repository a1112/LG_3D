import QtQuick
import "../../Base" as Base
Item{
    id: root

    required property var style

    height: root.style.topHeight
    width:ustb.width
    Base.USTB{
        style: root.style
        id:ustb
        height:parent.height
        MouseArea{
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onClicked: {
                root.style.applyTheme(root.style.isDark ? "light" : "dark")
            }
        }
    }
}
