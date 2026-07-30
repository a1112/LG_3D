import QtQuick 2.15
import QtQuick.Layouts

    Image {
        id: uSTB
        required property var style
        Layout.fillWidth: true
        source: uSTB.style.isDark
                ? uSTB.style.getIcon("USTB_Dark")
                : uSTB.style.getIcon("USTB_Light")
        fillMode: Image.PreserveAspectFit
    }

