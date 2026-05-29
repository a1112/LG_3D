import QtQuick
import QtQuick.Controls

ItemDelegate {
    id: root

    property string buttonType: "minimize"
    property string tipText: ""
    property color iconColor: coreStyle.labelColor
    property color hoverColor: buttonType === "close" ? "#C42B1C" : coreStyle.buttonHoverColor
    property color pressedColor: buttonType === "close" ? "#A4261D" : coreStyle.selectionColor

    width: coreStyle.windowButtonWidth
    height: coreStyle.topHeight
    padding: 0

    ToolTip.visible: tipText !== "" && hovered
    ToolTip.text: tipText

    background: Rectangle {
        color: root.pressed ? root.pressedColor : (root.hovered ? root.hoverColor : coreStyle.headerBackgroundColor)
        radius: 0
    }

    contentItem: Item {
        width: parent.width
        height: parent.height

        Canvas {
            id: iconCanvas
            anchors.centerIn: parent
            width: 18
            height: 18

            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.strokeStyle = root.hovered && root.buttonType === "close" ? "#FFFFFF" : root.iconColor
                ctx.lineWidth = 1.7
                ctx.lineCap = "square"

                if (root.buttonType === "minimize") {
                    ctx.beginPath()
                    ctx.moveTo(4, 10)
                    ctx.lineTo(14, 10)
                    ctx.stroke()
                } else if (root.buttonType === "restore") {
                    ctx.strokeRect(5, 7, 8, 7)
                    ctx.beginPath()
                    ctx.moveTo(8, 5)
                    ctx.lineTo(15, 5)
                    ctx.lineTo(15, 12)
                    ctx.stroke()
                } else if (root.buttonType === "maximize") {
                    ctx.strokeRect(4.5, 4.5, 9, 9)
                } else if (root.buttonType === "close") {
                    ctx.beginPath()
                    ctx.moveTo(5, 5)
                    ctx.lineTo(13, 13)
                    ctx.moveTo(13, 5)
                    ctx.lineTo(5, 13)
                    ctx.stroke()
                }
            }

            Connections {
                target: root
                function onHoveredChanged() { iconCanvas.requestPaint() }
                function onPressedChanged() { iconCanvas.requestPaint() }
                function onButtonTypeChanged() { iconCanvas.requestPaint() }
            }
            Connections {
                target: coreStyle
                function onLabelColorChanged() { iconCanvas.requestPaint() }
                function onHeaderBackgroundColorChanged() { iconCanvas.requestPaint() }
            }
        }
    }
}
