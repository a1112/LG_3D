import QtQuick
import QtQuick.Controls.Material
import "../Pages/Header"
CheckRec {
    width:30
    fillWidth:true
    property int currentShowModel: 0

    checked:dataShowCore.topDataManage.currentShowModel==currentShowModel

    MouseArea{
        anchors.fill:parent
        onClicked:{
            dataShowCore.topDataManage.currentShowModel = currentShowModel
        }
    }

    property bool selected:checked
    color:selected?Material.color(Material.Teal):coreStyle.labelsColor

    checkColor:selected?Material.color(Material.Teal):"#00000000"
}
