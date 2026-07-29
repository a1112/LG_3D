import QtQuick

import QtQuick.Layouts
import "../../Foot"

Item {
    id: root

    required property var controller
    required property var modelStore
    required property var surfaceData
    required property var style

    anchors.fill: parent

    Rectangle{
        color: root.style.itemDbackColor
        width: rowr.width
        height: rowr.height
        id:rect_id
        anchors.right: parent.right
        RowLayout{
            id:rowr
            Column{
                id:row
                ItemDelegateItem {
                    height: 20
                    text: qsTr("重置")
                    selected: false
                    font.bold:true
                    onClicked: {
                        root.controller.resetView()
                        // dataShowCore.telescopedJointView =! dataShowCore.telescopedJointView
                    }
                }
                ItemDelegateItem {
                    height: 20
                    text: root.modelStore.imageMaskChecked
                          ? qsTr("AREA") : qsTr("AREA_MASK")
                    selected: root.modelStore.imageMaskChecked
                    font.bold:true
                    visible: root.surfaceData.isAreaRootView
                    onClicked: {
                        root.modelStore.imageMaskChecked =
                                !root.modelStore.imageMaskChecked
                    }
                }
            }
        }
    }
}
