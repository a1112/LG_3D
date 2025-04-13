import QtQuick

import QtQuick.Layouts
import "../../Foot"

Item {
 anchors.fill: parent

    Rectangle{
        color: "#722f2f2f"
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
                    text: "重置"
                    selected: false
                    font.bold:true
                    onClicked: {
                        dataShowCore.resetView()
                        // dataShowCore.telescopedJointView =! dataShowCore.telescopedJointView
                    }
                }
            }
        }
    }
}
