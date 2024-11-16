import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id:root
    ListView{
        spacing: 5
    height: parent.height
    width: parent.width
    orientation: ListView.Horizontal
    model: surfaceData.viewDataModel

    delegate: ItemDelegate {
        height: root.height
        width: height
        Image {
            asynchronous: true
            source: image_source
            width: parent.width
            height: parent.height
            fillMode: Image.PreserveAspectFit
            sourceSize.width: parent.width
            sourceSize.height: parent.height
        }
        onClicked: {
                surfaceData.setViewSource(key)

        }
        onDoubleClicked: {
             surfaceData.setViewSource(key)
            dataShowCore.viewRendererListView = false
        }
        Label{
            anchors.centerIn: parent
            text: key
            background: Rectangle {
                color: "#2f2f2f"
                radius: 5
            }

        }
        Rectangle{
            width: parent.width
            height: 3
            color: "#0078D7"
            visible: surfaceData.currentViewKey === key
        }
        Rectangle{
            anchors.bottom: parent.bottom
            width: parent.width
            height: 3
            color: "#0078D7"
            visible: surfaceData.currentViewKey === key
        }
    }
    }

}
