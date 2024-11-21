import QtQuick

Item {
    id:root
    ListView{
    spacing:10
    anchors.fill: parent
    model:dataShowCore.pointData
    delegate: XYZShow{
        id:xyz
        width: root.width
        closeVis:true
        function get_zValue(){
            api.get_zValueData(surfaceData.key,surfaceData.coilId,
                               p_x,
                               p_y,
                               (result)=>{
                                   xyz.z_mm = (result*surfaceData.scan3dScaleZ-dataShowCore.medianZ).toFixed(2)
                               },
                               (error)=>{
                                   console.log("get_zValueData error:",error)
                               }
                            )
        }
        title:"点 "+index
        x_mm:dataShowCore.pxtoPos(p_x).toFixed(0)
        y_mm:dataShowCore.pxtoPos(p_y).toFixed(0)
        onX_mmChanged:{
           get_zValue()
        }
        onCloseClicked:{
            surfaceData.removeSignPoint(index)
        }

    }


    }

}
