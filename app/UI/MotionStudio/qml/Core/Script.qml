import QtQuick
import "Script"
// 数据自动计算脚本
Item {
    id: root
    required property var modelStore
    required property var leftController
    required property var toolService

property LeftListScript leftListScript: LeftListScript{
        modelStore: root.modelStore
        leftController: root.leftController
        toolService: root.toolService
    }



}
