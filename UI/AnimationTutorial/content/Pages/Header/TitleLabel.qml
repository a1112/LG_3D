import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
Label {
    Layout.alignment:Qt.AlignVCenter
    text: core.appTitle
    font.pixelSize: 26
    font.bold: true
    font.family: "Inter"
    color: coreStyle.rootTitleColor

    // Gradient {
    //     GradientStop { position: 0.0; color: "#333333" }
    //     GradientStop { position: 1.0; color: "#666666" }
    // }
}
