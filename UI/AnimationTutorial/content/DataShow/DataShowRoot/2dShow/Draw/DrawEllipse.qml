import QtQuick
import QtQuick.Shapes
import "../"
Item {
    anchors.fill: parent

    Shape {
        ShapePath{
            strokeWidth: 2
            strokeColor: "#aaa2b9bc"
            startX:dataShowCore.toPx()// surfaceData.inner_circle_centre[0]*dataShowCore.canvasScale
            startY: surfaceData.inner_circle_centre[1]*dataShowCore.canvasScale

            id:p
            PathLine{
                relativeX:dataShowCore.perpendicularPoint.x*dataShowCore.canvasScale-p.startX
                relativeY:dataShowCore.perpendicularPoint.y*dataShowCore.canvasScale-p.startY
            }
        }}
    CentreView{     // 圆心
        x: dataShowCore.toPx(inner_ellipse[0][0])// inner_ellipse[0][0]*dataShowCore.canvasScale
        y:dataShowCore.toPx(inner_ellipse[0][1])// inner_ellipse[0][1]*dataShowCore.canvasScale
    }
}
