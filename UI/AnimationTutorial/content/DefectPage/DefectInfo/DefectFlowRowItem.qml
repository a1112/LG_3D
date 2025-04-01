import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../btns"
import "../../Model/server"
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
