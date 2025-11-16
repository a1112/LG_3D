import QtQuick
import QtQuick.Controls
import "../../Model/server"
Rectangle{
    property DefectItemModel defectItem: DefectItemModel{
    }
    // property ServerDefectModel srverDefectModel: ServerDefectModel{
    // }

    // visible: dataShowCore_.defect_show(defectName) //dataAreaShowCore
    x: defectItem.defectX*dataShowCore_.canvasScale
    y: defectItem.defectY*dataShowCore_.canvasScale
    width: defectItem.defectW*dataShowCore_.canvasScale
    height: defectItem.defectH*dataShowCore_.canvasScale
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
