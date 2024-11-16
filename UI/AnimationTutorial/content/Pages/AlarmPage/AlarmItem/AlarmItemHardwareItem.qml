import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
ItemDelegate {
    id:root
    property string titleText: "磁盘"
    property string valueText: "20 %"
    property string msg_: ""
    property int level: 1
    property string valueColor:level>=3?Material.color(Material.Red) :level>=2?Material.color(Material.Yellow):coreStyle.labelColor
    ToolTip.text: msg_
    ToolTip.visible:hovered
    Frame{
        anchors.fill: parent
    }
    RowLayout{
        anchors.fill: parent
        Label{
            text:root.titleText
        }
        Label{
            text: ":"
        }
        Label{
            color: root.valueColor
            font.bold:true
            font.pixelSize: 18
            text: root.valueText
        }
    }

}
