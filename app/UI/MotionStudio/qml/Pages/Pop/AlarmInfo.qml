import QtQuick

// 深度信息报警相关显示
Row {
    id:root
    required property var hoverController

    spacing:0
    visible: root.hoverController.hovedCoilModel !== undefined

    AlarmInfoItem{
        alarmItemInfo: root.hoverController.hovedCoilModel
                       ? root.hoverController.hovedCoilModel.alarmItemInfo_L : null
        width:root.width/2
    }
    AlarmInfoItem{
        width:root.width/2
        alarmItemInfo: root.hoverController.hovedCoilModel
                       ? root.hoverController.hovedCoilModel.alarmItemInfo_S : null
    }
}
