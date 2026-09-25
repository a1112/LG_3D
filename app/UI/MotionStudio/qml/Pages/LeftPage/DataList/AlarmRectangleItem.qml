import QtQuick 2.15
import "../../../animation"
AnimRec {
    id: root

    required property var summary

    running:level>2
    runningOpacity:false
    property int level: 1
    implicitWidth: 6
    implicitHeight: width
    radius: 3
    color: root.summary.level2Color(root.level)
    scaleFrom:0.6
    scaleTo:3
}
