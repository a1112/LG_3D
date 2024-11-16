import QtQuick
import QtQuick.Controls.Material
TabBar{
    y:-6
    height: 35
    id:root
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
