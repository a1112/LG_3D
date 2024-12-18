import QtQuick
import QtQuick.Shapes
import "../"
Item {
    anchors.fill: parent

    Shape {
        id: preciseShape

        ShapePath {
            id: shapePath
            strokeWidth: 2
            strokeColor: "#aaa2b9bc"
            startX: dataShowCore.toPx() // surfaceData.inner_circle_centre[0]*dataShowCore.canvasScale
            startY: surfaceData.inner_circle_centre[1] * dataShowCore.canvasScale

            PathLine {
                relativeX: dataShowCore.perpendicularPoint.x * dataShowCore.canvasScale - shapePath.startX
                relativeY: dataShowCore.perpendicularPoint.y * dataShowCore.canvasScale - shapePath.startY
            }
        }

 }
    // MouseArea {
    //     anchors.fill: parent
    //     hoverEnabled: true

    //     onPositionChanged: {
    //         const mouseX = mouse.x;
    //         const mouseY = mouse.y;

    //         // 将鼠标位置映射到形状的坐标系
    //         const localX = mouseX - shapePath.startX;
    //         const localY = mouseY - shapePath.startY;

    //         // 判断鼠标是否接近路径（这里假设一个宽度阈值，10 像素）
    //         const threshold = 10;
    //         const lineX = dataShowCore.perpendicularPoint.x * dataShowCore.canvasScale - shapePath.startX;
    //         const lineY = dataShowCore.perpendicularPoint.y * dataShowCore.canvasScale - shapePath.startY;

    //         const distance = Math.abs((lineY - 0) * localX - (lineX - 0) * localY) /
    //             Math.sqrt(lineX ** 2 + lineY ** 2);

    //         if (distance <= threshold) {
    //             shapePath.strokeColor = "#ff0000"; // 鼠标接近路径时改变颜色
    //         } else {
    //             shapePath.strokeColor = "#aaa2b9bc"; // 鼠标离开路径范围时恢复颜色
    //         }
    //     }
    // }

    CentreView { // 圆心
        id: centrePoint
        x: dataShowCore.toPx(inner_ellipse[0][0])
        y: dataShowCore.toPx(inner_ellipse[0][1])

        // MouseArea {
        //     anchors.fill: parent
        //     hoverEnabled: true
        //     onPositionChanged: {
        //         const dx = mouse.x - centrePoint.x;
        //         const dy = mouse.y - centrePoint.y;
        //         const distance = Math.sqrt(dx * dx + dy * dy);
        //         const radius = 10; // 假设圆心的半径为 10 像素

        //         if (distance <= radius) {
        //             centrePoint.color = "yellow"; // 鼠标接近圆心时改变颜色
        //         } else {
        //             centrePoint.color = "white"; // 鼠标离开圆心时恢复颜色
        //         }
        //     }
        // }
    }
}
