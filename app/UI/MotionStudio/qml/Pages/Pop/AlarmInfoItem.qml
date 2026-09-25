import QtQuick
import QtQuick.Controls
import "../../Model"
Column {
    id: root

    property AlarmItemInfo alarmItemInfo:AlarmItemInfo{}
    Row{
    Label{
        text: root.alarmItemInfo.taperShapeMsg
    }
    }
}
