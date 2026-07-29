import QtQuick
import QtQuick.Controls
import "../fonts" as Fonts

Label {
    id: root

    property var fonts: Fonts.LoadFont {}
    readonly property date currentDate: core.nowTime

    text: Qt.formatDateTime(currentDate, "yyyy-MM-dd HH:mm:ss")
    font.family: fonts.timeFamioly || "Microsoft YaHei"
    font.pixelSize: adaptive.fontMetric(24, 18, 30)
    font.features: {"tnum": 1}
    color: coreStyle.isDark ? "#DDEBFF" : coreStyle.textColor
}
