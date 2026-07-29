import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
Label{
Layout.fillWidth: true

    background: Rectangle {
        color: coreStyle.panelAlternateColor
        border.color: coreStyle.headerBorderColor
        border.width: 1
        radius: coreStyle.controlRadius
    }

}
