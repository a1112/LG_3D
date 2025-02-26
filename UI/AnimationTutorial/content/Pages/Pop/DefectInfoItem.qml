import QtQuick
import QtQuick.Controls
import "../../Model/server"
Item {
    id:root
    property DefectItemModel defectItem:DefectItemModel{}
    property int currentCoilId: coilModel.coilId
    height: 100
    width: height
    Image {
        width:parent.width
        height:parent.height
        id: image_name
        source: root.defectItem.defect_url
        fillMode:Image.PreserveAspectFit
    }
    Component.onCompleted:{
        defectItem.init(defectModel.get(index))
    }
}
