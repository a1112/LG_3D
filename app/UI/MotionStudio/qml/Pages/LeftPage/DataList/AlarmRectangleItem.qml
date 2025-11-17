import QtQuick 2.15
import "../../../animation"
AnimRec {
    running:level>2
    runningOpacity:false
    property int level: 1
    implicitWidth: 6
    implicitHeight: width
    radius: 3
    color: listItemCoil.level2Color(level)
    scaleFrom:0.6
    scaleTo:3
}
