import QtQuick 2.15
import QtQuick.Layouts

    Image {
        id: uSTB
        Layout.fillWidth: true
        source: coreStyle.isDark ? coreStyle.getIcon("USTB_Dark") : coreStyle.getIcon("USTB_Light")
        fillMode: Image.PreserveAspectFit
    }

