import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
BaseLabel{
    Layout.fillWidth: true
    font.pixelSize: 18
    horizontalAlignment: Text.AlignHCenter
    font.bold: true
    background: Rectangle {
        color: palette.alternateBase
        radius: 5
    }

}
