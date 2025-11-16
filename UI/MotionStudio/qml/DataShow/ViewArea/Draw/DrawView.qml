import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
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

    // Rectangle{
    //    anchors.fill: parent
    //    transform:Rotation{
    //        // origin.x: ellipse.center.x;
    //        // origin.y: ellipse.center.y;
    //        angle:ellipse.angle
    //    }
    // }

    Shape {
        id: ellipseShape

        ShapePath {
            strokeWidth: 2
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

        }
    }
        Shape {
    ShapePath {
        strokeColor: "blue"
        strokeWidth: 1
        fillColor: "transparent"

        dashPattern: [ 2, 2 ]

        property int joinStyleIndex: 0
        startX: ellipse.center.x
        startY: ellipse.center.y
        PathLine {
            x: ellipse.axes.major_axis + ellipse.center.x
            y:ellipse.center.y

        }
        PathMove{
            x:ellipse.center.x + ellipse.axes.major_axis/2
            y:ellipse.center.y  - ellipse.axes.minor_axis/2
        }

        PathLine {

            x: ellipse.center.x + ellipse.axes.major_axis/2;
            y: ellipse.axes.minor_axis +ellipse.center.y  - ellipse.axes.minor_axis/2

        }
    }
    }
        Label{
            x:ellipse.center.x+ellipse.axes.major_axis/2+5
            y:ellipse.center.y - ellipse.axes.minor_axis * (1/3)
            text:surfaceData.ix_to_mm( inner_ellipse[1][1])
            color: "green"
            font.bold: true
            font.pointSize: 14
        }

        Label{
            x:ellipse["center"].x+ellipse.axes.major_axis*(2/3)
            y:ellipse["center"].y+5
            text:surfaceData.ix_to_mm( inner_ellipse[1][0])
            color: "green"
            font.bold: true
            font.pointSize: 14
        }
    Rectangle{
        width: 4
        height: 4
        radius: 2
        color:"#00000000"
        border.width: 2
        border.color: "orange"
        x:dataShowCore.perpendicularPoint.x*dataShowCore.canvasScale-2
        y:dataShowCore.perpendicularPoint.y*dataShowCore.canvasScale-2
    }

    // DrawEllipse{}// 绘制 拟合椭圆
    DrawSurvey{}// 绘制 测量

    DrawPoint{} // 绘制 标记点
}
