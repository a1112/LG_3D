import QtQuick
import QtQuick.Controls
import "../../Model/server"
Rectangle {
    property DefectItemModel defectItem:DefectItemModel{}
    property int currentCoilId: coilModel.coilId
    height: 100
    width: height

    Component.onCompleted:{
        defectItem.init(defectModel.get(index))
    }
}
