import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../Pages/Header"
Flow {
    width:parent.width
    height:implicitHeight
    anchors.margins: 1
    spacing: 5
    Layout.fillWidth: true
    Repeater{
        model:dataShowCore.currentDefectDictModel
        CheckRec{
            text:defectName+" "+num
            height:25
            checked:coreModel.defectDictAll[defectName]
            onCheckedChanged:{
                if (coreModel.defectDictAll[defectName]!==checked){
                coreModel.defectDictAll[defectName]=checked
                coreModel.flushDefectDictAll()
                    }
            }
        }
}
}
