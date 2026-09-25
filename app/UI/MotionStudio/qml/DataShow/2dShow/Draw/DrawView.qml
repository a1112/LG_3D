import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

Item {
    id: root

    required property var surfaceData
    required property var dataShowCore
    required property var style
    required property var apiClient

    anchors.fill: parent

    readonly property var innerEllipse: {
        const source = root.surfaceData.inner_ellipse
        const center = source && source.length > 0 && source[0]
                       ? source[0] : [0, 0]
        const axes = source && source.length > 1 && source[1]
                     ? source[1] : [0, 0]
        const angle = source && source.length > 2 ? source[2] : 0
        return [center, axes, angle]
    }
    readonly property var ellipse: {
        let center = innerEllipse[0] || [0, 0]
        let axes = innerEllipse[1] || [0, 0]
        let scale = Number(dataShowCore.canvasScale) || 0
        let major = (Number(axes[1]) || 0) * scale
        let minor = (Number(axes[0]) || 0) * scale
        return {
            center: {
                x: (Number(center[0]) || 0) * scale - major / 2,
                y: (Number(center[1]) || 0) * scale
            },
            axes: {
                major: major,
                minor: minor
            },
            angle: Number(innerEllipse[2]) || 0
        }
    }
    readonly property var lineData: surfaceData.lineData || []
    readonly property var perpendicularPoint:
        dataShowCore.perpendicularPoint

    function requestCanvasPaint() {
        lineCanvas.requestPaint()
        transactionCanvas.requestPaint()
    }

    onLineDataChanged: lineCanvas.requestPaint()
    onSurfaceDataChanged: requestCanvasPaint()
    onDataShowCoreChanged: requestCanvasPaint()
    Component.onCompleted: requestCanvasPaint()

    Connections {
        target: root.dataShowCore
        function onCanvasScaleChanged() {
            root.requestCanvasPaint()
        }
    }

    Connections {
        target: root.surfaceData.txModel
        ignoreUnknownSignals: true
        function onCountChanged() {
            transactionCanvas.requestPaint()
        }
        function onDataChanged() {
            transactionCanvas.requestPaint()
        }
    }

    Canvas {
        id: lineCanvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            let context = getContext("2d")
            context.clearRect(0, 0, width, height)
            context.lineWidth = 1
            context.strokeStyle = root.style.selectionColor
            context.setLineDash([10, 5])
            let scale = Number(root.dataShowCore.canvasScale) || 0
            for (let index = 0; index < root.lineData.length; ++index) {
                let line = root.lineData[index] || {}
                if (!line.pointL || !line.pointR)
                    continue
                context.beginPath()
                context.moveTo(line.pointL[0] * scale,
                               line.pointL[1] * scale)
                context.lineTo(line.pointR[0] * scale,
                               line.pointR[1] * scale)
                context.stroke()
            }
        }
    }

    Canvas {
        id: transactionCanvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            let context = getContext("2d")
            context.clearRect(0, 0, width, height)
            context.lineWidth = 2
            context.strokeStyle = root.style.statusErrorColor
            let scale = Number(root.dataShowCore.canvasScale) || 0
            let model = root.surfaceData.txModel
            for (let index = 0; index < model.count; ++index) {
                let line = model.get(index)
                context.beginPath()
                context.moveTo(line.startX * scale, line.startY * scale)
                context.lineTo(line.endX * scale, line.endY * scale)
                context.stroke()
            }
        }
    }

    Shape {
        ShapePath {
            strokeWidth: 2
            strokeColor: root.style.statusSuccessColor
            fillColor: root.style.infoOverlayColor

            PathSvg {
                path: "M " + root.ellipse.center.x + ","
                      + root.ellipse.center.y + " a "
                      + root.ellipse.axes.major / 2 + ","
                      + root.ellipse.axes.minor / 2 + " 0 1,0 "
                      + root.ellipse.axes.major + ",0 a "
                      + root.ellipse.axes.major / 2 + ","
                      + root.ellipse.axes.minor / 2 + " 0 1,0 -"
                      + root.ellipse.axes.major + ",0"
            }
        }
    }

    Shape {
        ShapePath {
            strokeColor: root.style.selectionColor
            strokeWidth: 1
            fillColor: "transparent"
            dashPattern: [2, 2]
            startX: root.ellipse.center.x
            startY: root.ellipse.center.y

            PathLine {
                x: root.ellipse.axes.major + root.ellipse.center.x
                y: root.ellipse.center.y
            }
            PathMove {
                x: root.ellipse.center.x + root.ellipse.axes.major / 2
                y: root.ellipse.center.y - root.ellipse.axes.minor / 2
            }
            PathLine {
                x: root.ellipse.center.x + root.ellipse.axes.major / 2
                y: root.ellipse.center.y + root.ellipse.axes.minor / 2
            }
        }
    }

    Label {
        x: root.ellipse.center.x + root.ellipse.axes.major / 2 + 5
        y: root.ellipse.center.y - root.ellipse.axes.minor / 3
        text: root.surfaceData.ix_to_mm(
                  Number(root.innerEllipse[1][1]) || 0)
        color: root.style.statusSuccessColor
        font.bold: true
    }

    Label {
        x: root.ellipse.center.x + root.ellipse.axes.major * 2 / 3
        y: root.ellipse.center.y + 5
        text: root.surfaceData.ix_to_mm(
                  Number(root.innerEllipse[1][0]) || 0)
        color: root.style.statusSuccessColor
        font.bold: true
    }

    Rectangle {
        width: 6
        height: 6
        radius: 3
        color: "transparent"
        border.width: 2
        border.color: root.style.statusWarningColor
        visible: root.perpendicularPoint !== undefined
                 && root.perpendicularPoint !== null
                 && isFinite(root.perpendicularPoint.x)
                 && isFinite(root.perpendicularPoint.y)
        x: visible
           ? root.perpendicularPoint.x * root.dataShowCore.canvasScale - 3 : 0
        y: visible
           ? root.perpendicularPoint.y * root.dataShowCore.canvasScale - 3 : 0
    }

    DrawSurvey {
        dataShowCore: root.dataShowCore
        style: root.style
    }
    DrawPoint {
        surfaceData: root.surfaceData
        dataShowCore: root.dataShowCore
        style: root.style
        apiClient: root.apiClient
        innerEllipse: root.innerEllipse
    }
}
