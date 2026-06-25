import QtQuick

Item {

    property string global_key: ""
    property var data
    property real out_circle_center_x: 0.0  // 外圈圆心x坐标
    property real out_circle_center_y: 0.0  // 外圈圆心y坐标
    property real out_circle_width: 0.0  // 外椭圆宽
    property real out_circle_height: 0.0  // 外椭圆高
    property real out_circle_radius: 0.0  // 外圈旋转角度
    property real inner_circle_center_x: 0.0  // 内圈圆心x坐标
    property real inner_circle_center_y: 0.0  // 内圈圆心y坐标
    property real inner_circle_width: 0.0  // 内椭圆宽
    property real inner_circle_height: 0.0  // 内椭圆高
    property real inner_circle_radius: 0.0  // 内圈旋转角度
    property real accuracy_x: 1.0
    property real accuracy_y: 1.0
    readonly property real innerDiameterMm: inner_circle_width > 0 ? inner_circle_width * accuracy_x : -1
    property var level: 0
    property var err_msg: ""
    property bool hasData:false

    function numberValue(value, defaultValue) {
        if (value === undefined || value === null) {
            return defaultValue
        }
        let numberValue_ = Number(value)
        return isFinite(numberValue_) ? numberValue_ : defaultValue
    }

    function init() {
        hasData=false
        out_circle_center_x=0
        out_circle_center_y=0
        out_circle_width=0
        out_circle_height=0
        out_circle_radius=0
        inner_circle_center_x=0
        inner_circle_center_y=0
        inner_circle_width=0
        inner_circle_height=0
        inner_circle_radius=0
        accuracy_x=1
        accuracy_y=1
        level=0
        err_msg=""
    }

    onDataChanged:{
        if (data){
            hasData=true
            out_circle_center_x=numberValue(data["out_circle_center_x"], 0)
            out_circle_center_y=numberValue(data["out_circle_center_y"], 0)
            out_circle_width=numberValue(data["out_circle_width"], 0)
            out_circle_height=numberValue(data["out_circle_height"], 0)
            out_circle_radius=numberValue(data["out_circle_radius"], 0)
            inner_circle_center_x=numberValue(data["inner_circle_center_x"], 0)
            inner_circle_center_y=numberValue(data["inner_circle_center_y"], 0)
            inner_circle_width=numberValue(data["inner_circle_width"], 0)
            inner_circle_height=numberValue(data["inner_circle_height"], 0)
            inner_circle_radius=numberValue(data["inner_circle_radius"], 0)
            accuracy_x=numberValue(data["accuracy_x"], 1)
            accuracy_y=numberValue(data["accuracy_y"], 1)
            level=numberValue(data["level"], 0)
            err_msg=data["err_msg"] || ""
        }
        else{
            init()
        }
    }



}
