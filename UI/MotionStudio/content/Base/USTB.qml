import QtQuick 2.15
import QtQuick.Layouts

    Image {
        id: uSTB
        Layout.fillWidth: true
        source: coreStyle.isDark? "../../icons/USTB_Dark.png":"../../icons/USTB_Light.png" //"../../images/USTB.png"
        fillMode: Image.PreserveAspectFit
    }

