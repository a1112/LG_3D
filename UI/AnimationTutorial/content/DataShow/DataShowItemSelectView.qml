import QtQuick
import QtQuick.Controls.Material
Item{
    implicitWidth: 30
    Pane {
        anchors.fill: parent
        Material.elevation:6
    }
    Rectangle{
        anchors.fill: parent
        color:"blue"
        opacity:0.1
    }
    Column{
        spacing: 5
        CheckRecItem{
            text: "塔形曲线".split("").join('\n')
            height:100
            currentShowModel:dataShowCore.topDataManage.lineShowModel

        }
        CheckRecItem{
            text: "数据".split("").join('\n')
            height:50
            currentShowModel:dataShowCore.topDataManage.dataInfoShowModel
        }

        CheckRecItem{
            text: "缺陷".split("").join('\n')
            height:50
            currentShowModel:dataShowCore.topDataManage.defectShowModel
        }
    }
}
