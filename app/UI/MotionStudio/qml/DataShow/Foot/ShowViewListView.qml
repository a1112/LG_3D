pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls


Item {
    id: root
    required property var surfaceData
    required property var controller
    required property var style
    implicitWidth: (implicitHeight + 5) * root.surfaceData.viewDataModel.count
    ListView{
        id: viewList
        spacing: 5
        height: parent.height
        width: parent.width
        orientation: ListView.Horizontal
        model: root.surfaceData.viewDataModel
        clip: true

        delegate: ItemDelegate {
            id: viewDelegate
            required property var model
            readonly property string viewKey: viewDelegate.model.key || ""
            height: root.height
            width: height
            enabled: viewDelegate.model.has_data === true
            opacity: enabled ? 1 : 0.35
            Image {
                asynchronous: true
                source: viewDelegate.enabled ? viewDelegate.model.image_source || "" : ""
                width: parent.width
                height: parent.height
                fillMode: Image.PreserveAspectFit
                sourceSize.width: parent.width
                sourceSize.height: parent.height
            }
            onClicked: {
                root.surfaceData.rootViewIndex = 0
                root.surfaceData.setViewSource(viewDelegate.viewKey)
            }
            onDoubleClicked: {
                root.surfaceData.setViewSource(viewDelegate.viewKey)
                root.controller.viewRendererListView = false
            }
            Label{
                anchors.centerIn: parent
                text: viewDelegate.viewKey
                color: root.style.textColor
                background: Rectangle {
                    color: root.style.infoOverlayColor
                    border.color: root.style.infoOverlayBorderColor
                    border.width: 1
                    radius: 5
                }

            }
            Rectangle{
                width: parent.width
                height: 3
                color: root.style.accentColor
                visible: root.surfaceData.currentViewKey === viewDelegate.viewKey
            }
            Rectangle{
                anchors.bottom: parent.bottom
                width: parent.width
                height: 3
                color: root.style.accentColor
                visible: root.surfaceData.currentViewKey === viewDelegate.viewKey
            }
        }
    }

}
