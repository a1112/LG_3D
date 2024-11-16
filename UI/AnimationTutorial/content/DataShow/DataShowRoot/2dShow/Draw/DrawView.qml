import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes
import "../../../../DataShow/ShowCharts"
import "../"
Item {
    id:root
    anchors.fill: parent
    property var inner_circle_centre: surfaceData.inner_circle_centre
    property var circle: [parseInt(inner_circle_centre[0]*dataShowCore.canvasScale),
        parseInt(inner_circle_centre[1]*dataShowCore.canvasScale),
        parseInt(inner_circle_centre[3]*dataShowCore.canvasScale),
        parseInt(inner_circle_centre[4]*dataShowCore.canvasScale)]
    property var inner_ellipse: surfaceData.inner_ellipse
    property var ellipse: {
        "center": {"x": inner_ellipse[0][0]*dataShowCore.canvasScale-inner_ellipse[1][1]*dataShowCore.canvasScale/2
            ,
            "y": inner_ellipse[0][1]*dataShowCore.canvasScale
        },
        "axes": {"major_axis": inner_ellipse[1][1]*dataShowCore.canvasScale,
            "minor_axis": inner_ellipse[1][0]*dataShowCore.canvasScale},
        "angle": inner_ellipse[2]
    }
    // [inner_ellipse[0][0]*dataShowCore.canvasScale,
    // inner_ellipse[0][1]*dataShowCore.canvasScale,
    // inner_ellipse[1][0]*dataShowCore.canvasScale,
    // inner_ellipse[1][1]*dataShowCore.canvasScale]
    property var lineData: surfaceData.lineData

    onLineDataChanged: {
        canva.requestPaint()
    }

    Canvas{
        id:canva
        anchors.fill: parent
        onPaint: {
            var context = getContext("2d")
            context.clearRect(0, 0, canva.width, canva.height)
            context.lineWidth = 1
            context.strokeStyle = "blue"
            context.setLineDash([10, 5])
            // 遍历线段列表进行绘制
            for (var i = 0; i < lineData.length; i++) {
                var line = lineData[i]
                context.beginPath()
                context.moveTo(line.pointL[0]*dataShowCore.canvasScale, line.pointL[1]*dataShowCore.canvasScale)
                context.lineTo(line.pointR[0]*dataShowCore.canvasScale, line.pointR[1]*dataShowCore.canvasScale)
                context.stroke()
            }
        }
    }

    Canvas{
        id:canva2
        anchors.fill: parent
        onPaint: {
            var context = getContext("2d")
            context.clearRect(0, 0, canva.width, canva.height)
            context.lineWidth = 2
            context.strokeStyle = "red"
            for (var i = 0; i < surfaceData.txModel.count; i++) {
                var line = surfaceData.txModel.get(i)
                context.beginPath()
                context.moveTo(line.startX*dataShowCore.canvasScale, line.startY*dataShowCore.canvasScale)
                context.lineTo(line.endX*dataShowCore.canvasScale, line.endY*dataShowCore.canvasScale)
                context.stroke()
            }
        }
    }
    Repeater{

        model:surfaceData.txModel
        // {"startX":4799,"startY":2405,"startZ":1777,"endX":4809,"endY":2404,"endZ":47266,"start_z_mm":-764.16,"end_z_mm":-25.899999999999977,"reverse":-1}

    }

    Shape {
        id: ellipseShape
        ShapePath {
            strokeWidth: 1
            strokeColor: "green"
            fillColor: "#12222222"

            // 计算旋转后的路径
            PathSvg {
                path: "M " +  ellipse.center.x + "," + ellipse.center.y + " " +
                      "a " + (ellipse.axes.major_axis / 2) + "," + (ellipse.axes.minor_axis / 2) + " 0 1,0 " +
                      ellipse.axes.major_axis + ",0 " +
                      "a " + (ellipse.axes.major_axis / 2) + "," + (ellipse.axes.minor_axis / 2) + " 0 1,0 -" +
                      ellipse.axes.major_axis + ",0"
            }

            // 使用 rotation 属性进行旋转
            // rotation: ellipse.angle
            // transformOrigin: Item.Center
        }

    }

    Shape {
        ShapePath{
            strokeWidth: 2
            strokeColor: "#aaa2b9bc"
            startX: surfaceData.inner_circle_centre[0]*dataShowCore.canvasScale
            startY: surfaceData.inner_circle_centre[1]*dataShowCore.canvasScale

            id:p
            PathLine{
                relativeX:dataShowCore.perpendicularPoint.x*dataShowCore.canvasScale-p.startX
                relativeY:dataShowCore.perpendicularPoint.y*dataShowCore.canvasScale-p.startY
            }
        }}

    CentreView{
        x: inner_ellipse[0][0]*dataShowCore.canvasScale
        y: inner_ellipse[0][1]*dataShowCore.canvasScale
    }
    Rectangle{
        width: 4
        height: 4
        radius: 2
        color:"#00000000"
        border.width: 1
        border.color: "orange"
        x:dataShowCore.perpendicularPoint.x*dataShowCore.canvasScale-2
        y:dataShowCore.perpendicularPoint.y*dataShowCore.canvasScale-2
        // Label{
        //     background: Rectangle{
        //         color: "#772e2e2e"
        //     }
        //     x:30
        //     text:"x:"+ ((dataShowCore.perpendicularPoint.x-surfaceData.inner_circle_centre[0])*surfaceData.scan3dScaleX).toFixed(1)
        // }
        // Label{
        //     background: Rectangle{
        //         color: "#772e2e2e"
        //     }
        //     y:30
        //     text:"y:"+ ((surfaceData.inner_circle_centre[1]-dataShowCore.perpendicularPoint.y)*surfaceData.scan3dScaleY).toFixed(1)
        // }
    }

    Repeater{
        model:dataShowCore.pointData
        delegate: Rectangle{
                            property real z_mm:0
            x:p_x*dataShowCore.canvasScale-4
            y:p_y*dataShowCore.canvasScale-4
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

                function get_zValue(){

                    api.get_zValueData(surfaceData.key,surfaceData.coilId,
                                       p_x,
                                       p_y,
                                       (result)=>{
                                            console.log(result)
                                           z_mm = (result*surfaceData.scan3dScaleZ-dataShowCore.medianZ).toFixed(2)
                                       },
                                       (error)=>{
                                           console.log("get_zValueData error:",error)
                                       }
                                    )
                }
                Component.onCompleted:get_zValue()
            }
        }

    }
    // Item{
    //     width:parent.width
    //     y:parent.height/2-50
    //     height:100
    //     DataShowItemCharts{  //  charts
    //         types:0
    //         anchors.fill: parent
    //     }
    // }

}
