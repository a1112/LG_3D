import QtQuick 2.15
import QtQuick.Controls 2.15
// 十字架
Item {
    anchors.fill: parent
    visible: true
    property real crossY: 0
    property real crossX: 0
    DashHLine{
        visible: dataShowCore.imageShowHovered
        lineWidth:1
        width: 20
        x:crossX-10
        y:crossY

    }
    Label{
    color: "red"
    text: dataShowCore.hoverdYmm+ " mm"
        anchors.left: parent.left
    z:-height
    y:crossY
    background: Rectangle{
        color: "black"
        radius: 5
    }
    }
    DashVLine{
        lineWidth:1
        height: 20
        z:-height
        x:crossX
        y:crossY-10
    }
    Label{
        anchors.bottom: parent.bottom
        color: "red"
        text:   dataShowCore.hoverdXmm+ "  mm"
        x:crossX
        background: Rectangle{
            color: "black"
            radius: 5
        }
    }

    Label{
        color:parseInt( dataShowCore.hoverdZmm)<surfaceData.tower_warning_threshold_down || parseInt( dataShowCore.hoverdZmm)>surfaceData.tower_warning_threshold_up?"red":"green" //三角测距
        text: dataShowCore.hoverdZmm
        y:crossY-30
        x:crossX-30
        scale:0.7
        background: Rectangle{
            color: "black"
            radius: 5
        }
    }
}
