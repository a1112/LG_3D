import QtQuick
import QtQuick.Controls

ItemDelegate {
    height: parent.height
    width: height
    property bool hasImage: false
    property string image_source: ""
    property string key: ""

    Image {
        id: err
        scale: 0.7
        anchors.centerIn: parent
        asynchronous: true
        source: coreStyle.getIcon("imageError")
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        sourceSize.width: parent.width
        sourceSize.height: parent.height
        Label {
            anchors.centerIn: parent
            text: "No image"
            visible: !hasImage
        }
    }
    Image {
        id: image
        asynchronous: true
        source: hasImage ? image_source : ""
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        sourceSize.width: parent.width
        sourceSize.height: parent.height
        onStatusChanged: {
            if (!hasImage || !source || status === Image.Error) {
                err.visible = true
            } else {
                err.visible = status !== Image.Loaded
            }
        }
    }
    Label {
        anchors.centerIn: parent
        text: key
        background: Rectangle {
            color: "#2f2f2f"
            radius: 5
        }
    }
}
