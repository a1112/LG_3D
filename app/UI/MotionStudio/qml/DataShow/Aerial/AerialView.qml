import QtQuick
import QtQuick.Controls
Item {
    id: root

    required property var controller
    required property var style

    width: 100
    height: root.controller.aspectRatio > 0
            ? width / root.controller.aspectRatio : width

    property real opacity_image: 0.4
    property alias source: image.source
    Rectangle {
        anchors.fill: parent
        color: root.style.infoOverlayColor
    }



    Image{
        opacity: 0.4
        id: image
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        sourceSize.width: parent.width
        sourceSize.height: parent.height
    }
    Rectangle{
        id:rec
    x: root.controller.canvasContentXaspectRatio * parent.width
    y: root.controller.canvasContentYaspectRatio * parent.height
     width: image.sourceSize.width * root.controller.canvasWidthAspectRatio
     height: image.sourceSize.height * root.controller.canvasHeightAspectRatio
     color: "transparent"
     border.color: root.style.selectionColor
     border.width: 1
    }

    HoverHandler{
        onHoveredChanged: {
            if(hovered){
                image.opacity = 1
            }else{
                image.opacity = root.opacity_image
            }
        }

    }
    MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor

            onPressed: {
                root.moveViewport(mouseX, mouseY)
                // dataShowCore.canvasWidth=rec.width/parent.width * dataShowCore.canvasContentWidth
                // dataShowCore.canvasHeight=rec.height/parent.height * dataShowCore.canvasContentHeight
            }

            onPositionChanged: {
                root.moveViewport(mouseX, mouseY)
                // dataShowCore.canvasWidth=rec.width/parent.width * dataShowCore.canvasContentWidth
                // dataShowCore.canvasHeight=rec.height/parent.height * dataShowCore.canvasContentHeight
            }
        }

    function moveViewport(mouseX, mouseY) {
        if (!root.controller.flick || width <= 0 || height <= 0) {
            return
        }
        const contentX = (mouseX - rec.width / 2) / width
                         * root.controller.canvasContentWidth
        const contentY = (mouseY - rec.height / 2) / height
                         * root.controller.canvasContentHeight
        const maximumX = Math.max(
                           0,
                           root.controller.canvasContentWidth
                           - root.controller.canvasWidth)
        const maximumY = Math.max(
                           0,
                           root.controller.canvasContentHeight
                           - root.controller.canvasHeight)
        root.controller.flick.contentX = Math.min(
                    Math.max(0, contentX), maximumX)
        root.controller.flick.contentY = Math.min(
                    Math.max(0, contentY), maximumY)
    }

}
