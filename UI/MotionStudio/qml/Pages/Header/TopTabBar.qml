import QtQuick
import QtQuick.Controls.Material
TabBar{
    y:-6
    height: 35
    id:root
    currentIndex:app_core.appIndex
    onCurrentIndexChanged:app_core.appIndex = currentIndex
    background: Rectangle {
        color: "#00000000"
    }

    TabButton{
        text: "数据分析"
        font.bold: true
        height: root.height
        font.pixelSize: 15
    }
    TabButton{
        text: "缺陷分析"
        font.bold: true
        height: root.height
        font.pixelSize: 15
    }
}
