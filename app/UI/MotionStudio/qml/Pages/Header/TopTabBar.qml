import QtQuick
import QtQuick.Controls.Material
TabBar{
    y: adaptive.headerOffset
    height: adaptive.headerTabHeight
    id:root
    currentIndex:app_core.appIndex
    onCurrentIndexChanged:app_core.appIndex = currentIndex
    background: Rectangle {
        color: coreStyle.headerBackgroundColor
    }

    TabButton{
        text: "数据分析"
        font.bold: true
        height: root.height
        font.pixelSize: adaptive.fontMetric(15, 13, 18)
    }
    TabButton{
        text: "缺陷分析"
        font.bold: true
        height: root.height
        font.pixelSize: adaptive.fontMetric(15, 13, 18)
    }
}
