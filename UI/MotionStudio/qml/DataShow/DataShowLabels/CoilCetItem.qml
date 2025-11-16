import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtGraphs
Column {
    id:root
Layout.fillWidth: true
property int mm_x: + (surfaceData.inner_circle_centre[0]*surfaceData.scan3dScaleX).toFixed(1)
property int mm_y: + (surfaceData.inner_circle_centre[1]*surfaceData.scan3dScaleY).toFixed(1)

RowLayout{
    width: parent.width
    spacing: 10
    Label{
        text: "原点:" + mm_x + "  |  " + mm_y
    }
}
}
