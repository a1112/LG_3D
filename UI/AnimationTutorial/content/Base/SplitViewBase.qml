import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls
import QtQuick.Controls.impl

T.SplitView {
    id: control
    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             implicitContentHeight + topPadding + bottomPadding)

    handle: Rectangle {
        implicitWidth: control.orientation === Qt.Horizontal ? 6 : control.width
        implicitHeight: control.orientation === Qt.Horizontal ? control.height : 6
        color: "#00000000"
        Rectangle{
        height: parent.height
        width: 2
        anchors.centerIn: parent
        color: T.SplitHandle.pressed ? control.palette.mid
            : (T.SplitHandle.hovered ? control.palette.midlight : "#000")
        }

    }
}
