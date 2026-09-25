import QtQuick
import QtQuick.Controls.Material
import "../../Pages/Header"
CheckRec {
    id: root

    required property var controller

    width:30
    fillWidth:true
    property int currentShowModel: 0

    checked: root.controller.topDataManage.currentShowModel === root.currentShowModel

    MouseArea{
        anchors.fill:parent
        onClicked:{
            root.controller.topDataManage.currentShowModel = root.currentShowModel
        }
    }

    property bool selected:checked
    color: selected ? Material.color(Material.Teal) : style.labelsColor

    checkColor: selected ? style.accentColor : style.headerBorderColor
}
