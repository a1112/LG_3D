import QtQuick

Item {

    property real image_gamma: 0.7
    property bool image_gamma_enable_btn: true
    readonly property bool image_is_gray: surfaceData ? surfaceData.currentViewKey=="GRAY" : false
    readonly property bool image_gamma_enable: image_gamma_enable_btn && image_is_gray


}
