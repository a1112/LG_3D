import QtQuick
import QtQuick.Controls
Column{
    id:root
    property alias title: titleItem.text
    property real value: 0

    Label{
        id:titleItem
        text: "Z轴旋转"
    }
    Item{
        width: dia.width/2
        height: dia.height/2
Dial{
    anchors.centerIn: parent
    width: implicitWidth
    height: implicitHeight
    id:dia
    scale: 0.5

    wrap: true
    startAngle: 0
    endAngle: 360
    from: 0
    to: 360
    value: root.value
    onValueChanged: root.value = value
    Label{
        scale: 2
        anchors.centerIn: parent
        text: (dia.value).toFixed(0)
    }
}


}
    }
