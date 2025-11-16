import QtQuick

XYZShow{
    id:root
    function get_zValue(){
        api.get_zValueData(surfaceData.key,surfaceData.coilId, dataShowCore.perpendicularPointX, dataShowCore.perpendicularPointY,
                           (result)=>{
                               mm_z = (result*surfaceData.scan3dScaleZ-dataShowCore.medianZ).toFixed(2)
                           },
                           (error)=>{
                               console.log("get_zValueData error:",error)
                           }
                        )
    }


    property real mm_x: dataShowCore .perpendicularPointXmm.toFixed(0)
    onMm_xChanged:{
        get_zValue()
    }

    property real mm_y: dataShowCore .perpendicularPointYmm.toFixed(0)
    onMm_yChanged:{
        get_zValue()
    }
    property real mm_z:0
    title: "垂足"
    x_mm: mm_x
    y_mm: mm_y
    z_mm: mm_z
    // text_color:"orange"
}
