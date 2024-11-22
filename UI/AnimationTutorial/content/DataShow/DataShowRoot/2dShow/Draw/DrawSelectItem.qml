import QtQuick
import "../../../../Base"
SelectItem{
startX:dataShowCore.controls.surveyStartPointX
startY:dataShowCore.controls.surveyStartPointY
endX:dataShowCore.controls.surveyEndPointX
endY:dataShowCore.controls.surveyEndPointY
property real drawWidth:root.endX-root.startX
property real drawHeight:root.endY-root.startY

id:root
color:"#000078D7"
border.width: 0
LabelBase{
    background:Rectangle{
        color:coreStyle.backColor
    }
    text: dataShowCore.toMm(Math.abs(drawWidth)).toFixed(0) +" mm"
    anchors.horizontalCenter:parent.horizontalCenter
    anchors.bottom:parent.top
}
LabelBase{
    background:Rectangle{
        color:coreStyle.backColor
    }
    text: dataShowCore.toMm(Math.abs(drawHeight)).toFixed(0) +" mm"
    anchors.verticalCenter:parent.verticalCenter
    anchors.left:parent.right
    rotation: 90

}
LabelBase{
    x:(parent.width-width)/2
    y:(parent.height-height)/2+10
    background:Rectangle{
        color:coreStyle.backColor
    }
    text: dataShowCore.toMm(Math.sqrt(drawHeight**2+drawWidth**2)).toFixed(0) +" mm"

    rotation: Math.atan((drawHeight)/(drawWidth))*180/Math.PI

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
        onPaint: {
            var ctx = getContext("2d");
            ctx.fillStyle=Qt.rgba(0, 1, 1, 0.02)
            ctx.strokeStyle = Qt.rgba(1, 0, 0, 1)
            ctx.setLineDash([5,5])
            ctx.lineWidth = 1
            if(drawWidth*drawHeight>0){
                ctx.beginPath()
                ctx.moveTo(0, 0)
                ctx.lineTo(root.width, 0)
                ctx.lineTo(root.width, root.height)
                ctx.stroke()
                ctx.fill()
                ctx.setLineDash([])
                ctx.beginPath()
                ctx.moveTo(0, 0)
                ctx.lineTo(root.width, root.height)
                ctx.stroke()  // 绘制线条

            }
            else{
                ctx.beginPath()
                ctx.moveTo(root.width, 0)
                ctx.lineTo(root.width, root.height)
                ctx.lineTo(0, root.height)
                ctx.stroke()
                ctx.fill()
                ctx.setLineDash([])
                ctx.beginPath()
                ctx.moveTo(root.width, 0)
                ctx.lineTo(0, root.height)
                ctx.stroke()  // 绘制线条
            }


        }
    }
}
