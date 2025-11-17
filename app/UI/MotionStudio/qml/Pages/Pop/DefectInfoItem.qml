import QtQuick
import QtQuick.Controls
import "../../Model/server"
Item {
    id:root
    property DefectItemModel defectItem:DefectItemModel{}
    property int currentCoilId: coilModel.coilId
    height: 150
    width: height
    visible: leftCore.isShowDefect(defectItem.defectName)
    Image {
        width:parent.width
        height:parent.height
        id: image_name
        source: root.defectItem.defect_url
        fillMode:Image.PreserveAspectFit
    }
    Label{
        font.bold:true
        font.pointSize:16
        anchors.horizontalCenter:parent.horizontalCenter
        text:defectItem.defectName
        anchors.bottom:parent.bottom
        color:Qt.lighter(defectItem.defectColor)
        background:Rectangle{
            color:"#88000000"
        }
    }

    Component.onCompleted:{
        defectItem.init(defectModel.get(index))
    }
}
