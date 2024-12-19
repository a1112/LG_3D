import QtQuick

Item {
    id: root
    property real ellipseWidth
    property real ellipseHeight
    property real canvasSizeWidth: Math.min(root.width, root.height)
    property real ellipseRotation

    property real centerX: canvasSizeWidth / 2
    property real centerY: canvasSizeWidth / 2

    // Color and text properties
    property string ellipseFillColor: "#32FF0000"
    property string ellipseStrokeColor: "#EEE"
    property int lineWidth: 2
    property string longAxisText: "731"
    property string longAxisTextColor: "green"
    property string shortAxisText: "722"
    property string shortAxisTextColor: "blue"

    Item {
        width: canvasSizeWidth
        height: canvasSizeWidth
        anchors.centerIn: parent
        Canvas {
            id: canvas
            anchors.fill: parent
            rotation: ellipseRotation
            onPaint: {
                var ctx = canvas.getContext("2d")
                ctx.clearRect(0, 0, canvas.width, canvas.height) // Clear the canvas

                // Set the style
                ctx.fillStyle = root.ellipseFillColor  // Fill color
                ctx.strokeStyle = root.ellipseStrokeColor // Border color
                ctx.lineWidth = root.lineWidth       // Border thickness

                // Draw ellipse
                ctx.beginPath()
                let dw = root.ellipseWidth * canvasSizeWidth
                let dh = root.ellipseHeight * canvasSizeWidth
                ctx.ellipse(centerX - dw / 2, centerY - dh / 2, dw, dh, 0, 0, 2 * Math.PI) // x, y, radiusX, radiusY, rotation, startAngle, endAngle
                ctx.fill()
                ctx.stroke()
                ctx.globalCompositeOperation = "destination-out"

                // Draw a circle over the ellipse
                ctx.fillStyle = "#FFF" // Make the circle transparent
                ctx.strokeStyle = root.ellipseStrokeColor
                ctx.beginPath()
                ctx.arc(centerX, centerY, Math.min(dw,dh) / 2, 0, 2 * Math.PI) // x, y, radius, startAngle, endAngle
                // ctx.stroke()
                ctx.fill()
                ctx.stroke()
                ctx.globalCompositeOperation = "source-over"
                // Draw axes and labels
                ctx.setLineDash([5, 5]) // Draw dashed lines
                ctx.strokeStyle = root.ellipseStrokeColor
                ctx.beginPath()
                ctx.moveTo(centerX, centerY - dh / 2)
                ctx.lineTo(centerX, centerY + dh / 2)
                ctx.moveTo(centerX - dw / 2, centerY)
                ctx.lineTo(centerX + dw / 2, centerY)
                ctx.stroke()
                ctx.setLineDash([]) // Reset line dash

                // Label the axes
                ctx.font = "21px Arial"
                ctx.fillStyle = root.longAxisTextColor
                ctx.fillText(root.longAxisText, centerX + dw / 2 - 40, centerY)
                ctx.fillStyle = root.shortAxisTextColor
                ctx.fillText(root.shortAxisText, centerX - 20, centerY - dh / 2 + 40)


            }
        }
    }
}
