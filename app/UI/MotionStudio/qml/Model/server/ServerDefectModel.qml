import QtQuick

Item {
    id: root
    required property var controller
    required property var defectClassController
    required property var rawDefect

    function p_t_x_m_c(p){
        return root.controller.px_to_pos_x_mm_from_centre(p).toFixed(0)
    }
    function p_t_y_m_c(p){
        return root.controller.px_to_pos_y_mm_from_centre(p).toFixed(0)
    }
    function p_t_w_m(p){
        return root.controller.px_to_width_mm(p).toFixed(0)
    }
    function p_t_h_m(p){
        return root.controller.px_to_height_mm(p).toFixed(0)
    }

    readonly property string defect_name: rawDefect.defectName || ""
    readonly property string config_defect_name: rawDefect.configDefectName || defect_name
    readonly property real defect_x: Number(rawDefect.defectX) || 0
    readonly property string defect_x_mm: p_t_x_m_c(defect_x)
    readonly property real defect_y: Number(rawDefect.defectY) || 0
    readonly property string defect_y_mm: p_t_y_m_c(defect_y)
    readonly property real defect_w: Math.max(0, Number(rawDefect.defectW) || 0)
    readonly property string defect_w_mm: p_t_w_m(defect_w)
    readonly property real defect_h: Math.max(0, Number(rawDefect.defectH) || 0)
    readonly property string defect_h_mm: p_t_h_m(defect_h)
    readonly property bool isArea: Boolean(rawDefect.is_area)
                                   || root.defectClassController.is_area_defect_name(config_defect_name)
}
