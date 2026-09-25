import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import "../Base"
Item{
    id:root
    property alias show_text: cd.text
    property color textColor: "#ffffff"
    Material.accent:showColor
    property alias recWidth: cd.width
    property alias recHeight: cd.height
    property color showColor: "#fff"
    property color bgColor: "#fff"
    property alias mouseEnabled: cd.enabled
    property alias checked: cd.checked
    implicitWidth: 30
    width: implicitWidth
    height: width
    signal clicked
    CheckBox{
        HoverHandler{
            cursorShape:Qt.PointingHandCursor
        }
        id:cd
        indicator.width: parent.height*0.5
        indicator.height:indicator.width
        onClicked: {
            root.clicked()
        }
    }
}
