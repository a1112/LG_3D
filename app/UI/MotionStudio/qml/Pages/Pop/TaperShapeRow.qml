import QtQuick
import QtQuick.Controls

Row {
    id: root

    required property var style
    required property var data
    required property string surfaceLabel

    spacing: 1

    readonly property real cellWidth: (width - spacing * 5) / 6

    Label {
        width: root.cellWidth
        height: root.height
        text: root.surfaceLabel
        color: root.style.titleColor
        font.bold: true
        font.pixelSize: 12
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        background: Rectangle {
            color: root.style.panelAlternateColor
        }
    }

    TaperPointCell {
        width: root.cellWidth
        height: root.height
        style: root.style
        data: root.data
        xKey: "out_taper_max_x"
        yKey: "out_taper_max_y"
        valueKey: "out_taper_max_value"
        emphasizePositive: true
    }

    TaperPointCell {
        width: root.cellWidth
        height: root.height
        style: root.style
        data: root.data
        xKey: "out_taper_min_x"
        yKey: "out_taper_min_y"
        valueKey: "out_taper_min_value"
    }

    TaperPointCell {
        width: root.cellWidth
        height: root.height
        style: root.style
        data: root.data
        xKey: "in_taper_max_x"
        yKey: "in_taper_max_y"
        valueKey: "in_taper_max_value"
        emphasizePositive: true
    }

    TaperPointCell {
        width: root.cellWidth
        height: root.height
        style: root.style
        data: root.data
        xKey: "in_taper_min_x"
        yKey: "in_taper_min_y"
        valueKey: "in_taper_min_value"
    }

    Label {
        width: root.cellWidth
        height: root.height
        text: root.data.rotation_angle === undefined
              || root.data.rotation_angle === null
              ? "-" : root.data.rotation_angle
        color: root.style.labelColor
        font.pixelSize: 11
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
