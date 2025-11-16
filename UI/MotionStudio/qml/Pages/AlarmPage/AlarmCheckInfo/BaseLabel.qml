import QtQuick
import QtQuick.Controls
import "../../../Labels"
BaseLabel {
    ToolTip.visible: hh.hovered
    font.pointSize: 16
    font.bold: true
    opacity: 0.7
    HoverHandler{
        id:hh
    }
}
