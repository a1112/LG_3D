import QtQuick
import QtQuick.Controls.Material
import "../../../../Model/server"
CheckDelegate {

    property int defectNum:dataShowCore.getNumByDefectName(defectClassItemModel.defectName)

    visible: defectClassItemModel.defectShow || dataShowCore.defectManage.un_defect_show //dataShowCore.defectManage.defect_is_show(defectName)
    property DefectClassItemModel defectClassItemModel:DefectClassItemModel{}
    checked: global.defectClassProperty.defectDictAll[defectClassItemModel.defectName]??false// defectClassItemModel.defectShow
    text: defectNum+" "+defectClassItemModel.defectName  // num
    font.bold:true
    Material.foreground: defectClassItemModel.defectColor
    onCheckedChanged:{
        if (coreModel.defectDictAll[defectClassItemModel.defectName]!==checked){
                coreModel.defectDictAll[defectClassItemModel.defectName]=checked
                coreModel.flushDefectDictAll()
            }
        }

    Component.onCompleted:{
        defectClassItemModel.init(this)
    }

    Label{
        anchors.bottom:parent.top
        x:15
        text: " x"

    }
    Rectangle{
        width:1
        height:parent.height
        anchors.right:parent.right
        color: defectClassItemModel.defectShow?Material.color(Material.Orange):Material.color(Material.Green)
    }
}
// CheckRec{
// text:defectName+" "+num
// height:25
// width:100
// fillWidth:true
// checked:coreModel.defectDictAll[defectName]
// onCheckedChanged:{
//     if (coreModel.defectDictAll[defectName]!==checked){
//     coreModel.defectDictAll[defectName]=checked
//     coreModel.flushDefectDictAll()
//         }
// }





// CheckRec{
// text:defectName+" "+num
// height:30
// width:100
// // fillWidth:true
// checked:coreModel.defectDictAll[defectName]
// onCheckedChanged:{
//     if (coreModel.defectDictAll[defectName]!==checked){
//     coreModel.defectDictAll[defectName]=checked
//     coreModel.flushDefectDictAll()
//         }
// }

