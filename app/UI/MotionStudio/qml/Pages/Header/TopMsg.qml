import QtQuick
import QtQuick.Controls.Material
import "../../Base" as Base
Row{
    id: root

    required property var authManager
    required property var modelStore
    required property var coreController
    required property var globalContext
    required property var style

    visible: root.authManager.isAdmin
    spacing: 40
Base.DropShadowLabel{
    text: "最新"
    color: Material.color(Material.Orange)
    visible: root.modelStore.isListRealModel && root.coreController.isLast
}
Base.DropShadowLabel{
    text: root.modelStore.isListRealModel ? "实时" : "历史"
    color: root.modelStore.currentCoilListTextColor
}
Base.DropShadowLabel{
    text: root.globalContext.screenConfig.width > 2000
          ? "     Local Model !" : "Loc"
    visible: root.coreController.isLocal
    color:  Material.color(Material.Pink)
    layer.enabled: true
}
CheckRec{
    style: root.style
    Material.foreground: Material.color(Material.Yellow)
    visible: root.modelStore.currentCoilListIndex === 1
    implicitWidth: 35
    typeIndex:1
    checkColor: Material.color(Material.Green)
    text: "<-返回实时"
    fillWidth: true
    checked: root.modelStore.imageMaskChecked
    onClicked:{
    root.modelStore.currentCoilListIndex = 0
    }
}
Base.DropShadowLabel{
    visible: root.authManager.isAdmin
             && root.globalContext.screenConfig.width > 2000
    text: root.coreController.currentCoilModel.coilNo
    font: Qt.font({
        family: "Microsoft YaHei",
        pixelSize: 18,
        bold: true
    })
    layer.enabled: true
}
}
