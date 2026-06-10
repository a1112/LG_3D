import QtQuick
import QtQuick.Controls
import "../../Model/server"
Item {
    id:root
    property DefectItemModel defectItem:DefectItemModel{}
    property var defectData
    property bool respectFilter: false
    property int thumbnailSize: 96
    height: thumbnailSize
    width: height
    visible: !respectFilter || leftCore.isShowDefect(defectItem.defectName)
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
        text:root.defectItem.defectName
        anchors.bottom:parent.bottom
        color:Qt.lighter(root.defectItem.defectColor)
        background:Rectangle{
            color:"#88000000"
        }
    }

    onDefectDataChanged: {
        defectItem.init(defectData)
    }

    Component.onCompleted:{
        defectItem.init(defectData)
    }
}
