import QtQuick
import QtQuick.Controls
import "../../../../Model/server"
MenuItem {
    property DefectClassItemModel defectClass:DefectClassItemModel{}
    text:defectClass.defectName

    // visible:defectClass.defectShow
    checked:defectClass.defectShow
    Rectangle{
        anchors.top:parent.top
        height:1
        width:parent.width
        color:global.defectClassProperty.getColorByLevel(defectClass.defectLevel)
        opacity:0.7
    }
    Rectangle{
        width:10
        anchors.right:parent.right
        height:parent.height
        visible: defectClass.defectName == defect.defect_name
        color:global.defectClassProperty.getColorByName(defectClass.defectName)
    }

    onClicked:{
        defect.setCheckDefectName(defectClass.defectName)
    }

}
