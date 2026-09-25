import QtQuick
import QtQuick.Controls.Material
TabBar{
    id:root

    required property var adaptiveMetrics
    required property var style
    required property var appController

    y: root.adaptiveMetrics.headerOffset
    height: root.adaptiveMetrics.headerTabHeight
    currentIndex: root.appController.appIndex
    onCurrentIndexChanged:
        root.appController.appIndex = root.currentIndex
    background: Rectangle {
        color: root.style.headerBackgroundColor
    }

    TabButton{
        text: "数据分析"
        height: root.height
        font: Qt.font({
            pixelSize: root.adaptiveMetrics.fontMetric(15, 13, 18),
            bold: true
        })
    }
    TabButton{
        text: "缺陷分析"
        height: root.height
        font: Qt.font({
            pixelSize: root.adaptiveMetrics.fontMetric(15, 13, 18),
            bold: true
        })
    }
}
