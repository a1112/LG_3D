import QtQuick
import QtQuick.Controls.Material
import "../../Base" as Base
Row{
    visible:auth.isAdmin
    spacing: 40
Base.DropShadowLabel{
    text: "最新"
    color: Material.color(Material.Orange)
    visible:coreModel.isListRealModel && core.isLast
}
Base.DropShadowLabel{
    text: coreModel.isListRealModel? "实时" :"历史"
    color: coreModel.currentCoilListTextColor
}
Base.DropShadowLabel{
    text:global.screenConfig.width>2000?"     Local Model !":"Loc"
    visible: core.isLocal
    color:  Material.color(Material.Pink)
    layer.enabled: true
}
CheckRec{
    Material.foreground: Material.color(Material.Yellow)
    visible: coreModel.currentCoilListIndex==1
    implicitWidth: 35
    typeIndex:1
    checkColor: Material.color(Material.Green)
    text: "<-返回实时"
    fillWidth: true
    checked:  coreModel.imageMaskChecked
    onClicked:{
    coreModel.currentCoilListIndex=0
    }
}
Base.DropShadowLabel{
    visible:auth.isAdmin && global.screenConfig.width>2000
    text: core.currentCoilModel.coilNo
    font.family: "Microsoft YaHei"
    font.pixelSize: 18
    font.bold: true
    layer.enabled: true
}
}
