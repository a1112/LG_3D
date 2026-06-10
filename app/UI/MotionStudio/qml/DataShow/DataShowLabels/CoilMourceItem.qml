import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtGraphs

XYZShow{
    id:root
property real mm_x: dataShowCore.hoverdXmm.toFixed(0)

property real mm_y: dataShowCore.hoverdYmm.toFixed(0)
property real mm_z:dataShowCore.hoverdZmm

title: qsTr("鼠标位置")
x_mm: mm_x
y_mm: mm_y
z_mm: mm_z
}
