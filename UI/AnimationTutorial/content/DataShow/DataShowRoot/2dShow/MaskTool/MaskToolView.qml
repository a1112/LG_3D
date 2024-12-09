import QtQuick

import QtQuick.Layouts
import QtQuick.Controls
import "../../../Foot"

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

                // ItemDelegateItem {
                //     height: 20
                //     text: "塔形"
                //     selected: dataShowCore.telescopedJointView
                //     onClicked: {
                //         dataShowCore.telescopedJointView =! dataShowCore.telescopedJointView
                //     }
                // }
                // Rectangle{
                //     width: row.width
                //     height: 1
                //     color: "#0090E0"
                // }
                // ItemDelegateItem {
                //     height: 20
                //     text: "数据"
                //     selected: dataShowCore.viewDefectListView
                //     onClicked: {
                //         dataShowCore.viewDefectListView=! dataShowCore.viewDefectListView
                //     }
                // }
            }
        }
    }
}
