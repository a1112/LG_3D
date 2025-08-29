import QtQuick
import QtQuick.Controls
import "../../Model/server"
Rectangle{
    property DefectItemModel defectItem: DefectItemModel{
    }
    // property ServerDefectModel srverDefectModel: ServerDefectModel{
    // }

    visible: dataShowCore.defect_show(defectName) //dataAreaShowCore
    x: defectItem.defectX*dataAreaShowCore.canvasScale
    y: defectItem.defectY*dataAreaShowCore.canvasScale
    width: defectItem.defectW*dataAreaShowCore.canvasScale
    height: defectItem.defectH*dataAreaShowCore.canvasScale
    border.color: defectItem.defectColor
    border.width: 2
    opacity:0.7
    color: "transparent"
    // visible: global.defectClassProperty.defectDictAll[defectName]??false
Label{
    visible:global.defectClassProperty.defeftDrawShowLasbel
    color: Qt.lighter(defectItem.defectColor)
    text: defectItem.defectName
    font.pixelSize: 15
    anchors.left: parent.right
    background:Rectangle{
        opacity:1
        color:"#000"
    }
}
Component.onCompleted:{
    defectItem.init(repeater.model.get(index))
}
}
