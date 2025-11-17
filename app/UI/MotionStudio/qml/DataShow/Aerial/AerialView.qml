import QtQuick
import QtQuick.Controls
Item {
    id:root
    width: 100
    height: width/dataShowCore_.aspectRatio

    property real zoom: width/dataShowCore_.aspectRatio

    property real opacity_image: 0.4
    property alias source: image.source
    Rectangle {
        anchors.fill: parent
        color: "#23000000"
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
    x:dataShowCore_.canvasContentXaspectRatio*parent.width
    y:dataShowCore_.canvasContentYaspectRatio*parent.height
     width: image.sourceSize.width* dataShowCore_.canvasWidthAspectRatio
     height: image.sourceSize.height* dataShowCore_.canvasHeightAspectRatio
     color:"#00000000"
     border.color: "blue"
     border.width: 1
    }

    HoverHandler{
        onHoveredChanged: {
            if(hovered){
                image.opacity = 1
            }else{
                image.opacity = opacity_image
            }
        }

    }
    MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor

            onPressed: {
                let contentX=(mouseX-rec.height/2)/parent.width * dataShowCore_.canvasContentWidth
                let contentY=(mouseY-rec.height/2)/parent.height * dataShowCore_.canvasContentHeight
                dataShowCore_.flick.contentX = Math.min(Math.max(0,contentX),dataShowCore_.canvasContentWidth-dataShowCore_.canvasWidth)
                dataShowCore_.flick.contentY = Math.min(Math.max(0,contentY),dataShowCore_.canvasContentHeight-dataShowCore_.canvasHeight)
                // dataShowCore.canvasWidth=rec.width/parent.width * dataShowCore.canvasContentWidth
                // dataShowCore.canvasHeight=rec.height/parent.height * dataShowCore.canvasContentHeight
            }

            onPositionChanged: {
                let contentX=(mouseX-rec.height/2)/parent.width * dataShowCore.canvasContentWidth
                let contentY=(mouseY-rec.height/2)/parent.height * dataShowCore.canvasContentHeight
                dataShowCore_.flick.contentX = Math.min(Math.max(0,contentX),dataShowCore_.canvasContentWidth-dataShowCore_.canvasWidth)
                dataShowCore_.flick.contentY = Math.min(Math.max(0,contentY),dataShowCore_.canvasContentHeight-dataShowCore_.canvasHeight)
                // dataShowCore.canvasWidth=rec.width/parent.width * dataShowCore.canvasContentWidth
                // dataShowCore.canvasHeight=rec.height/parent.height * dataShowCore.canvasContentHeight
            }
        }


}
