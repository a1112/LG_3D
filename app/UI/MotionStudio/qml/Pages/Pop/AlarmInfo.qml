import QtQuick

// 深度信息报警相关显示
Row {
    id:root
    spacing:0
    visible: leftCore.hovedCoilModel !== undefined

    AlarmInfoItem{
        alarmItemInfo: leftCore.hovedCoilModel ? leftCore.hovedCoilModel.alarmItemInfo_L : null
        width:root.width/2
    }
    AlarmInfoItem{
        width:root.width/2
        alarmItemInfo: leftCore.hovedCoilModel ? leftCore.hovedCoilModel.alarmItemInfo_S : null
    }
}
