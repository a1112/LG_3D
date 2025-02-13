import QtQuick
import QtQuick.Controls
import "../../Model"
Column {
    property AlarmItemInfo alarmItemInfo:AlarmItemInfo{}
    Row{
    Label{
        text: alarmItemInfo.taperShapeMsg
    }
    }
}
