import QtQuick 2.15
import QtQuick.Controls 2.15
Item {
    id:root
    width: 100
    height: width/dataShowCore.aspectRatio

    property real zoom: width/dataShowCore.aspectRatio

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
    x:dataShowCore.canvasContentXaspectRatio*parent.width
    y:dataShowCore.canvasContentYaspectRatio*parent.height
     width: image.sourceSize.width* dataShowCore.canvasWidthAspectRatio
     height: image.sourceSize.height* dataShowCore.canvasHeightAspectRatio
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
                let contentX=(mouseX-rec.height/2)/parent.width * dataShowCore.canvasContentWidth
                let contentY=(mouseY-rec.height/2)/parent.height * dataShowCore.canvasContentHeight
                dataShowCore.flick.contentX = Math.min(Math.max(0,contentX),dataShowCore.canvasContentWidth-dataShowCore.canvasWidth)
                dataShowCore.flick.contentY = Math.min(Math.max(0,contentY),dataShowCore.canvasContentHeight-dataShowCore.canvasHeight)
                // dataShowCore.canvasWidth=rec.width/parent.width * dataShowCore.canvasContentWidth
                // dataShowCore.canvasHeight=rec.height/parent.height * dataShowCore.canvasContentHeight
            }

            onPositionChanged: {
                let contentX=(mouseX-rec.height/2)/parent.width * dataShowCore.canvasContentWidth
                let contentY=(mouseY-rec.height/2)/parent.height * dataShowCore.canvasContentHeight
                dataShowCore.flick.contentX = Math.min(Math.max(0,contentX),dataShowCore.canvasContentWidth-dataShowCore.canvasWidth)
                dataShowCore.flick.contentY = Math.min(Math.max(0,contentY),dataShowCore.canvasContentHeight-dataShowCore.canvasHeight)
                // dataShowCore.canvasWidth=rec.width/parent.width * dataShowCore.canvasContentWidth
                // dataShowCore.canvasHeight=rec.height/parent.height * dataShowCore.canvasContentHeight
            }
        }


}
