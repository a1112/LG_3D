pragma ComponentBehavior: Bound

import QtQuick 2.15
import "../"
Item {
    id: backgroundRoot
    required property var adaptiveMetrics
    required property var style
    required property var leftView
    required property var rightView

    implicitWidth: backgroundRoot.adaptiveMetrics.designWidth
    implicitHeight: backgroundRoot.adaptiveMetrics.designHeight
    Rectangle {
        anchors.fill: parent
        color: backgroundRoot.style.panelBackgroundColor
    }
    property int tooolWidth: 0
    property bool is_half: backgroundRoot.leftView.visible && backgroundRoot.rightView.visible
    property int viewWidth_half: (backgroundRoot.width - backgroundRoot.tooolWidth) / 2
    property int viewWidth: backgroundRoot.width - backgroundRoot.tooolWidth
    Loader{
        clip:true
        anchors.fill:parent
        active: !(backgroundRoot.leftView.visible || backgroundRoot.rightView.visible)
        asynchronous:true
        sourceComponent: Watermark {
            anchors.fill:parent
            style: backgroundRoot.style
         }
    }

}
