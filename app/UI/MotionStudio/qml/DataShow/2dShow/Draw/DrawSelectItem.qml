import QtQuick
import "../../../Base"
SelectItem {
    id: root

    required property var dataShowCore
    required property var style

    startX: root.dataShowCore.controls.surveyStartPointX
    startY: root.dataShowCore.controls.surveyStartPointY
    endX: root.dataShowCore.controls.surveyEndPointX
    endY: root.dataShowCore.controls.surveyEndPointY
    property real drawWidth: root.endX - root.startX
    property real drawHeight: root.endY - root.startY

    color: "transparent"
    border.width: 0

LabelBase {
    background: Rectangle{
        color: root.style.panelElevatedColor
    }
    text: root.dataShowCore.toMm(Math.abs(root.drawWidth)).toFixed(0) + " mm"
    anchors.horizontalCenter:parent.horizontalCenter
    anchors.bottom:parent.top
}
LabelBase{
    background:Rectangle{
        color: root.style.panelElevatedColor
    }
    text: root.dataShowCore.toMm(Math.abs(root.drawHeight)).toFixed(0) + " mm"
    anchors.verticalCenter:parent.verticalCenter
    anchors.left:parent.right
    rotation: 90

}
LabelBase{
    x:(parent.width-width)/2
    y:(parent.height-height)/2+10
    background:Rectangle{
        color: root.style.panelElevatedColor
    }
    text: root.dataShowCore.toMm(
              Math.sqrt(root.drawHeight ** 2 + root.drawWidth ** 2)
          ).toFixed(0) + " mm"

    rotation: Math.atan2(root.drawHeight, root.drawWidth) * 180 / Math.PI
}

Canvas {
// transform: Rotation {
// angle :180
// origin.x:root.width/2
// origin.y:root.height/2

// axis { x: 0; y: 1; z: 0}
// }
    id:canva
        width: parent.width
        height: parent.height
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.fillStyle=Qt.rgba(0, 1, 1, 0.02)
            ctx.strokeStyle = root.style.statusErrorColor
            ctx.setLineDash([5,5])
            ctx.lineWidth = 1
            if (root.drawWidth * root.drawHeight > 0) {
                ctx.beginPath()
                ctx.moveTo(0, 0)
                ctx.lineTo(root.width, 0)
                ctx.lineTo(root.width, root.height)
                ctx.stroke()
                ctx.fill()
                ctx.closePath()
                ctx.setLineDash([])
                ctx.beginPath()
                ctx.moveTo(0, 0)
                ctx.lineTo(root.width, root.height)
                ctx.stroke()  // 绘制线条
                ctx.closePath()

            }
            else{
                ctx.beginPath()
                ctx.moveTo(root.width, 0)
                ctx.lineTo(root.width, root.height)
                ctx.lineTo(0, root.height)
                ctx.stroke()
                ctx.fill()
                ctx.closePath()
                ctx.setLineDash([])
                ctx.beginPath()
                ctx.moveTo(root.width, 0)
                ctx.lineTo(0, root.height)
                ctx.stroke()  // 绘制线条
                ctx.closePath()
            }


        }
    }

    onDrawWidthChanged: canva.requestPaint()
    onDrawHeightChanged: canva.requestPaint()
}
