import QtQuick
import QtQuick.Controls
Item {
    visible:coreModel.toolDict["adjust"]
    id:root
    height: warningLine.height + renderSetting.height+10

    Column{
    id:column
    width:parent.width
    spacing: 5
    WarningLine{
        id:warningLine
        // 预警线
    }
    RenderSetting{
        id:renderSetting
        // 渲染设置
    }
    }
    Rectangle{
        color:"transparent"
        anchors.fill: parent
        border.color: Material.color(Material.Blue)
        border.width: 1
    }

}
