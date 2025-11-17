import QtQuick
import "../../../Model/server"

Item {

    property ServerDefectModel defect: ServerDefectModel{}
    signal set_max(var defect)

    function setDefectShowView(defect_){
        console.log("setDefectShowView")
        defect=defect_
        // 设置到 100%
        set_max(defect_)
        // flick.contentX =defect.defect_x-(flick.width-defect.defect_w)/2
        // flick.contentY = defect.defect_y-(flick.height-defect.defect_h)/2

    }

}
