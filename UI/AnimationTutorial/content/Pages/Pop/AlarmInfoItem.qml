import QtQuick
import "../../Model"
Column {
    property AlarmItemInfo alarmItemInfo:AlarmItemInfo{}
    Row{
    Text{
        text: alarmItemInfo.taperShapeMsg

    }

    }

}
