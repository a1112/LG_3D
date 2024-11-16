import QtQuick 2.15

Canvas {
    id:root
    property int space: 4
    onHeightChanged: {
        requestPaint()
    }
    property int lineWidth: 1
    width: lineWidth
    property var fillStyle: Qt.rgba(1, 0, 0, 1)
    property var strokeStyle: Qt.rgba(1, 0, 0, 1)
    onPaint: {
        var ctx = getContext("2d");
        ctx.moveTo(0,0)
        ctx.lineWidth=lineWidth
        ctx.fillStyle=fillStyle
        ctx.strokeStyle = strokeStyle
        // ctx.setLineDash([space,15])
        ctx.lineTo(0,root.height)
        ctx.stroke()
    }
}
