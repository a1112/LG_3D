import QtQuick
import QtQuick.Controls.Material
    // 切换 全屏等
ColorItemDelegateButtonBase{
    tipText:qsTr("独占/取消独占")
    height: parent.height
    width: height
    selectColor:Material.color(Material.Green)
    property bool shouMaxIcon: true
    source:shouMaxIcon?coreStyle.getIcon("WindowScreen"):coreStyle.getIcon("FullScreen")
}
