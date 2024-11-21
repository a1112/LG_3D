import QtQuick
import "../../../../Base"
SelectItem{
startX:dataShowCore.controls.surveyStartPointX
startY:dataShowCore.controls.surveyStartPointY
endX:dataShowCore.controls.surveyEndPointX
endY:dataShowCore.controls.surveyEndPointY
id:root
color:"#030078D7"
border.width: 2
LabelBase{
    background:Rectangle{
        color:coreStyle.backColor
    }
    text: dataShowCore.toMm(Math.abs(dataShowCore.controls.surveyEndPointX-dataShowCore.controls.surveyStartPointX)).toFixed(0) +" mm"
    anchors.horizontalCenter:parent.horizontalCenter
    anchors.bottom:parent.top
}
LabelBase{
    background:Rectangle{
        color:coreStyle.backColor
    }
    text: dataShowCore.toMm(Math.abs(dataShowCore.controls.surveyEndPointY-dataShowCore.controls.surveyStartPointY)).toFixed(0) +" mm"
    anchors.verticalCenter:parent.verticalCenter
    anchors.left:parent.right
    rotation: 90

}

Canvas {
        width: parent.width
        height: parent.height
        onPaint: {
            var ctx = getContext("2d");
            ctx.beginPath();
            ctx.moveTo(0, 0)  // 起点 (50, 50)
            ctx.lineTo(root.width, root.height);  // 终点 (350, 350)
            ctx.stroke();  // 绘制线条
        }
    }
}
