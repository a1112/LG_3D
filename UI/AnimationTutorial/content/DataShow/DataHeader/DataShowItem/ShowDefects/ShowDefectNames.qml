import QtQuick
import QtQuick.Layouts
import "../../../../Pages/Header"
Flow {
    width:parent.width
    height:implicitHeight
    anchors.margins: 1
    spacing: 15
    Layout.fillWidth: true
    Repeater{
        model:dataShowCore.currentDefectDictModel
        CheckRec{
            text:defectName+" "+num
            height:30
            width:100
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
