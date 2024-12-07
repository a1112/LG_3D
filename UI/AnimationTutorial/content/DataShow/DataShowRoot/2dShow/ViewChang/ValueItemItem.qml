import QtQuick
import QtQuick.Controls
Item {
    height:itemHeight
    width:35
    Rectangle{
        width:3
        height:1

    }
    Label{
        text:getValueByModelIndex(index)
        anchors.centerIn:parent
    }
}
