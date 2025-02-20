import QtQuick
import "../../../Model/server"

Item {

    property ServerDefectModel defect: ServerDefectModel{}
    function setDefectShowView(defect_){
        defect=defect_
        // 设置到 100%
        dataShowCore.setToMaxScale()
        flick.contentX =defect.defect_x-(flick.width-defect.defect_w)/2
        flick.contentY = defect.defect_y-(flick.height-defect.defect_h)/2

    }

}
