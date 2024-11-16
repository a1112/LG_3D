import QtQuick
import QtQuick.Controls
ItemDelegate {
        height: parent.height
        width: height
        property bool hasImage:false
        Image {
            id:err
            scale:0.7
            anchors.centerIn: parent
            asynchronous: true
            source: "../../icons/imageError.jpg"
            width: parent.width
            height: parent.height
            fillMode: Image.PreserveAspectFit
            sourceSize.width: parent.width
            sourceSize.height: parent.height
            Label{
                anchors.centerIn: parent
                text: "无图片"
                visible: ! hasImage
            }
        }
        Image {
            id:image
            asynchronous: true
            source:hasImage?image_source:""
            width: parent.width
            height: parent.height
            fillMode: Image.PreserveAspectFit
            sourceSize.width: parent.width
            sourceSize.height: parent.height
            onStateChanged: {
                if (state == Image.Loaded) {
                err.visible = true
                }
                else
                    err.visible = false

            }


        }


        Label{
            anchors.centerIn: parent
            text: key
            background: Rectangle {
                color: "#2f2f2f"
                radius: 5
            }
    }
}
