import QtQuick
import QtQuick.Controls.Material
    // 切换 全屏等
ColorItemDelegateButtonBase{
    id: root
    required property var style
    tipText:qsTr("独占/取消独占")
    height: parent.height
    width: height
    selectColor:Material.color(Material.Green)
    property bool shouMaxIcon: true
    source: root.shouMaxIcon
            ? root.style.getIcon("WindowScreen")
            : root.style.getIcon("FullScreen")
}
