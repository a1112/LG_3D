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
            text: "塔\n形\n曲\n线"
            height:100
        }
        CheckRecItem{
            text: "数\n据"
            height:50
        }

        CheckRecItem{
            text: "缺\n陷"
            height:50
        }
    }
}
