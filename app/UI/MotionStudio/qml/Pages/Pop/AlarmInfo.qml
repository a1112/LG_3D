import QtQuick

// 深度信息报警相关显示
Row {
    id:root
    spacing:0

    AlarmInfoItem{
        alarmItemInfo: leftCore.hovedCoilModel.alarmItemInfo_L
        width:root.width/2
    }
    AlarmInfoItem{
        width:root.width/2
        alarmItemInfo: leftCore.hovedCoilModel.alarmItemInfo_S
    }
}
