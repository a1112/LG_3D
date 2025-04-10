import QtQuick
import QtQuick.Controls.Material
import "../Base"
LabelBase {
    id:root
    property bool running: true
    color: baseColor

    property color baseColor: Material.color( Material.Blue)
    property color errorColor: Material.color( Material.Red)

    SequentialAnimation on color{
         loops: Animation.Infinite
         running:root.running
    ColorAnimation {
        from: root.baseColor
        to: root.errorColor
        duration: 500
    }
    ColorAnimation {
        from:   root.errorColor
        to:     root.baseColor
        duration: 500
    }
    }
}
