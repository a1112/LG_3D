import QtQuick.Controls
import "../../../Controls/Menu"
Menu {
    id: root

    required property var controller
    required property var surfaceData
    required property var defectClassController

    title: qsTr("显示")

    Menu{
        title: "缺陷显示"
        Menu{
            title : qsTr("缺陷标签")
                SelectMenuItem{
                    text: qsTr("显示")
                    selectd: root.defectClassController.defeftDrawShowLasbel
                    onClicked: root.defectClassController.defeftDrawShowLasbel = true
                }
                SelectMenuItem{
                    text: qsTr("隐藏")
                    selectd: !root.defectClassController.defeftDrawShowLasbel
                    onClicked: root.defectClassController.defeftDrawShowLasbel = false
                }
        }
    }

    Menu{
        title: qsTr("深度显示")
        SelectMenuItem{
            text: qsTr("mm 相对值")
            selectd: root.surfaceData.currentPointValueShowType
                     === root.surfaceData.mm_pointValueShowType
            onClicked: root.surfaceData.currentPointValueShowType =
                       root.surfaceData.mm_pointValueShowType
        }
        SelectMenuItem{
            text: qsTr("mm 绝对值")
            selectd: root.surfaceData.currentPointValueShowType
                     === root.surfaceData.mm_int_pointValueShowType
            onClicked: root.surfaceData.currentPointValueShowType =
                       root.surfaceData.mm_int_pointValueShowType
        }
        SelectMenuItem{
            text: qsTr("int 原始值")
            selectd: root.surfaceData.currentPointValueShowType
                     === root.surfaceData.int_pointValueShowType
            onClicked: root.surfaceData.currentPointValueShowType =
                       root.surfaceData.int_pointValueShowType
        }
    }

}
