import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../../Pages/Header"
Item {
    height:30
    Layout.fillWidth: true
    Pane{
        anchors.fill:parent
        Material.elevation:5
    }
    ListView{
        anchors.fill:parent
        spacing:5
        model:dataShowCore.currentDefectDictModel
        orientation:ListView.Horizontal
        delegate:CheckRec{
            text:defectName+" "+num
            height:30
            width:100
            // fillWidth:true
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
