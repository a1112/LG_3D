pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    required property var style
    required property int index
    required property int selectedIndex
    required property var coil_id
    required property var time
    required property var width_
    required property var location_S
    required property var location_L
    required property var location_laser
    required property var median_3d_mm_S
    required property var median_3d_mm_L
    required property var total_length
    required property var total_error
    required property var distance_s_error
    required property var distance_l_error

    signal activated(int rowIndex, var coilId)

    color: index === selectedIndex
           ? style.selectionColor
           : index % 2 === 0
             ? style.panelBackgroundColor : style.panelAlternateColor

    function formatValue(value) {
        let number = Number(value)
        return isFinite(number) ? number.toFixed(3) : ""
    }

    RowLayout {
        anchors.fill: parent
        spacing: 8

        Cell { cellWidth: 90; text: root.coil_id }
        Cell { cellWidth: 160; text: root.time }
        Cell { cellWidth: 90; text: root.formatValue(root.width_) }
        Cell { cellWidth: 110; text: root.formatValue(root.location_S) }
        Cell { cellWidth: 110; text: root.formatValue(root.location_L) }
        Cell {
            cellWidth: 110
            text: root.formatValue(root.location_laser)
        }
        Cell {
            cellWidth: 120
            text: root.formatValue(root.median_3d_mm_S)
        }
        Cell {
            cellWidth: 120
            text: root.formatValue(root.median_3d_mm_L)
        }
        Cell {
            cellWidth: 140
            text: root.formatValue(root.total_length)
        }
        Cell {
            cellWidth: 150
            text: root.formatValue(root.total_error)
        }
        Cell {
            cellWidth: 150
            text: root.formatValue(root.distance_s_error)
        }
        Cell {
            cellWidth: 150
            text: root.formatValue(root.distance_l_error)
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.activated(root.index, root.coil_id)
    }

    component Cell: Label {
        required property real cellWidth
        Layout.preferredWidth: cellWidth
        color: root.style.textColor
        elide: Text.ElideRight
    }
}
