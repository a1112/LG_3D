import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

AbstractButton {
    id: root

    required property var style

    property string buttonType: "minimize"
    property string tipText: ""
    property color iconColor: root.style.labelColor
    property color hoverColor: buttonType === "close" ? "#C42B1C"
                                                       : root.style.buttonHoverColor
    property color pressedColor: buttonType === "close" ? "#A4261D"
                                                         : root.style.selectionColor

    width: root.style.windowButtonWidth
    height: root.style.topHeight
    implicitWidth: root.style.windowButtonWidth
    implicitHeight: root.style.topHeight
    Layout.preferredWidth: root.style.windowButtonWidth
    Layout.preferredHeight: root.style.topHeight
    Layout.fillHeight: false
    padding: 0
    spacing: 0
    hoverEnabled: true

    ToolTip.visible: tipText !== "" && hovered
    ToolTip.text: tipText

    background: Rectangle {
        anchors.fill: parent
        color: root.pressed ? root.pressedColor
                            : (root.hovered ? root.hoverColor
                                            : root.style.headerBackgroundColor)
        radius: 0
        border.width: 0
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
                target: root.style
                function onLabelColorChanged() { iconCanvas.requestPaint() }
                function onHeaderBackgroundColorChanged() { iconCanvas.requestPaint() }
            }
        }
    }
}
