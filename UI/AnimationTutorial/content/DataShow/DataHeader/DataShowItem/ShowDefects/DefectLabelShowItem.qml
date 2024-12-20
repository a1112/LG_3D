import QtQuick
import QtQuick.Controls.Material
CheckDelegate {
    text: defectName  // num
    font.bold:true
    Material.foreground:global.defectClassProperty.getColorByName(defectName)
    onCheckedChanged:{
        if (coreModel.defectDictAll[defectName]!==checked){
        coreModel.defectDictAll[defectName]=checked
        coreModel.flushDefectDictAll()
            }
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

