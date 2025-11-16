import QtQuick

Item {
    function p_t_m_c(p){
        return dataShowCore.px_to_pos_x_mm_from_centre(p).toFixed(0)
    }
    function p_t_w_m(p){
        return dataShowCore.px_to_width_mm(p).toFixed(0)
    }
    function p_t_h_m(p){
        return dataShowCore.px_to_height_mm(p).toFixed(0)
    }
    property var defect_x: defectX
    property var defect_x_mm: p_t_m_c(defect_x)
    property var defect_y: defectY
    property var defect_y_mm: p_t_m_c(defect_y)
    property var defect_w: defectW
    property var defect_w_mm:p_t_w_m(defect_w)
    property var defect_h: defectH
    property var defect_h_mm:p_t_h_m(defect_h)

    property var defect_name:defectName

    property var isArea : is_area

    function setCheckDefectName(check_defect_name){
        // 设置新的名称
        defect_name = check_defect_name
        api.set_check_defect_name(check_defect_name)
    }

}
