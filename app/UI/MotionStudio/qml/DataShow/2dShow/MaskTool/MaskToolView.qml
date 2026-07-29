import QtQuick

import QtQuick.Layouts
import "../../Foot"

Item {
 anchors.fill: parent

    Rectangle{
        color: coreStyle.itemDbackColor
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
                        dataShowCore_.resetView()
                        // dataShowCore.telescopedJointView =! dataShowCore.telescopedJointView
                    }
                }
                ItemDelegateItem {
                    height: 20
                    text: coreModel.imageMaskChecked ? qsTr("AREA") : qsTr("AREA_MASK")
                    selected: coreModel.imageMaskChecked
                    font.bold:true
                    visible: surfaceData.isAreaRootView
                    onClicked: {
                        coreModel.imageMaskChecked = !coreModel.imageMaskChecked
                    }
                }
            }
        }
    }
}
