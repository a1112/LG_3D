import QtQuick
import QtQuick.Controls
Rectangle{
    id:root
function get_zValue(){
    api.get_zValueData(surfaceData.key,surfaceData.coilId,
                       p_x,
                       p_y,
                       (result)=>{
                           z_mm = (result*surfaceData.scan3dScaleZ-dataShowCore.medianZ).toFixed(2)
                       },
                       (error)=>{
                           console.log("get_zValueData error:",error)
                       }
                    )
}

property real z_mm:0
x:dataShowCore.toPx(p_x)-4
y:dataShowCore.toPx(p_y)-4
width: 8
height: 8
radius: 4
color:"#00000000"
border.width: 2
border.color: "green"
Label{
background: Rectangle{
    color: "#772e2e2e"
}
color:"yellow"
anchors.right: parent.left
anchors.top: parent.bottom
anchors.horizontalCenterOffset:15
anchors.verticalCenterOffset:15
text:z_mm
}
Component.onCompleted:get_zValue()
}
