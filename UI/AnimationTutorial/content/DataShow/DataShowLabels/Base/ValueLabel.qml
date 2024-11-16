import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
Label{
Layout.fillWidth: true

    background: Rectangle {
        color: coreStyle.isDark?"black":"#eee"
        radius: 5
    }

}
