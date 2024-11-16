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
    property var level: 0
    property var err_msg: ""
    property bool hasData:true

    onDataChanged:{
        if (data){
            hasData=true
            out_circle_center_x=data["out_circle_center_x"]
            out_circle_center_y=data["out_circle_center_y"]
            out_circle_width=data["out_circle_width"]
            out_circle_height=data["out_circle_height"]
            out_circle_radius=data["out_circle_radius"]
            inner_circle_center_x=data["inner_circle_center_x"]
            inner_circle_center_y=data["inner_circle_center_y"]
            inner_circle_width=data["inner_circle_width"]
            inner_circle_height=data["inner_circle_height"]
            inner_circle_radius=data["inner_circle_radius"]
            level=data["level"]
            err_msg=data["err_msg"]
        }
        else{
            hasData=false
        }
    }



}
