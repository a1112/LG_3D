import QtQuick

Item {
    id: root

    required property var surfaceData

    property real image_gamma: 0.7
    property bool image_gamma_enable_btn: true
    readonly property bool image_is_gray: root.surfaceData.currentViewKey === "GRAY"
    readonly property bool image_gamma_enable: root.image_gamma_enable_btn
                                               && root.image_is_gray


}
