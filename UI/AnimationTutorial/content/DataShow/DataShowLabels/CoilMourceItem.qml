import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtGraphs

XYZShow{
    id:root
    function get_zValue(){
        api.get_zValueData(surfaceData.key,surfaceData.coilId, dataShowCore.hoverdX, dataShowCore.hoverdY,
                           (result)=>{
                               mm_z = (result*surfaceData.scan3dScaleZ-dataShowCore.medianZ).toFixed(2)
                           },
                           (error)=>{
                               console.log("get_zValueData error:",error)
                           }
                           )
    }


property real mm_x: dataShowCore .hoverdXmm.toFixed(0)
onMm_xChanged:{
    get_zValue()
}

property real mm_y: dataShowCore .hoverdYmm.toFixed(0)
onMm_yChanged:{
    get_zValue()
}
property real mm_z:0
onMm_zChanged:{
    dataShowCore.hoverdZmm = mm_z
}

title: "鼠标位置"
x_mm: mm_x
y_mm: mm_y
z_mm: mm_z
}
