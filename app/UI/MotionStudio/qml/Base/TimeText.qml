import QtQuick
import QtQuick.Controls
import "../fonts" as Fonts

Label {
    id: root

    required property var coreController
    required property var adaptiveMetrics
    required property var style

    property var fonts: Fonts.LoadFont {}
    readonly property date currentDate: root.coreController.nowTime

    text: Qt.formatDateTime(root.currentDate, "yyyy-MM-dd HH:mm:ss")
    font.family: root.fonts.timeFamioly || "Microsoft YaHei"
    font.pixelSize: root.adaptiveMetrics.fontMetric(24, 18, 30)
    font.features: {"tnum": 1}
    color: root.style.titleColor
}
