import QtQuick
import QtQuick.Controls.Material
import "../../../Model/server"
CheckDelegate {
    height:25
    property DefectClassItemModel defectClass:DefectClassItemModel{}
    text:defectClass.defectName
    Material.accent:defectClass.defectColor
    visible:defectClass.defectShow
    checked:defectClass.defectShow
    onCheckedChanged:{
        leftCore.setLiewViewFilterClass(defectClass.defectName,checked)
    }

}
