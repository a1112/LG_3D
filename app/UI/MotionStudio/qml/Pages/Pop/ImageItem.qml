import QtQuick
import QtQuick.Controls

ItemDelegate {
    id: root

    required property string image_source
    required property string key
    required property var style

    height: parent.height
    width: height
    property bool hasImage: false

    Image {
        id: err
        scale: 0.7
        anchors.centerIn: parent
        asynchronous: true
        source: root.style.getIcon("imageError")
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        sourceSize.width: parent.width
        sourceSize.height: parent.height
        Label {
            anchors.centerIn: parent
            text: "No image"
            visible: !root.hasImage
        }
    }
    Image {
        id: image
        asynchronous: true
        source: root.hasImage ? root.image_source : ""
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        sourceSize.width: parent.width
        sourceSize.height: parent.height
        onStatusChanged: {
            if (!root.hasImage || !source || status === Image.Error) {
                err.visible = true
            } else {
                err.visible = status !== Image.Ready
            }
        }
    }
    Label {
        anchors.centerIn: parent
        text: root.key
        background: Rectangle {
            color: "#2f2f2f"
            radius: 5
        }
    }
}
