import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import "../Base"
Item{
    property alias show_text: cd.text
    property color textColor: textColor
    Material.accent:showColor
    id:root
    property alias recWidth: cd.width
    property alias recHeight: cd.height
    property color showColor: "#fff"
    property color bgColor: "#fff"
    property alias mouseEnabled: cd.enabled
    property alias checked: cd.checked
    width: 0.3*dpi
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
